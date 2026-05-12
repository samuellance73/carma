import logging
import json
import os
import time
import litellm
from src import config

# Set up logging for this module
logger = logging.getLogger('llm_client')

# Configure LiteLLM logging
litellm.set_verbose = True 
logging.getLogger("litellm").setLevel(logging.INFO)

# Set environment variables for LiteLLM based on our Strong/Weak naming
# We need to set the actual provider keys that LiteLLM expects
def _apply_key(model: str | None, api_key: str | None):
    """Apply an API key to the correct env var for the given model provider."""
    if not api_key or not model:
        return
    if "gemini" in model.lower():
        os.environ["GEMINI_API_KEY"] = api_key
    elif "groq" in model.lower():
        os.environ["GROQ_API_KEY"] = api_key

_apply_key(config.STRONG_MODEL, config.STRONG_MODEL_API_KEY)
_apply_key(config.WEAK_MODEL, config.WEAK_MODEL_API_KEY)

async def ask(
    prompt: str,
    *,
    images: list[dict] | None = None,
    system: str | None = None,
    systemprompt: str | None = None,
    history: list[dict] | None = None,
    model: str | None = None,
    temperature: float = 1.0,
    max_tokens: int = 1024,
) -> str:
    """
    Send a prompt (and optional images) to an LLM via LiteLLM.
    Automatically chooses STRONG_MODEL if images are present, else WEAK_MODEL.
    """
    system_instruction = system or systemprompt

    # Auto-select model if not provided
    if model is None:
        if images:
            model = config.STRONG_MODEL
        else:
            model = config.WEAK_MODEL

    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    
    if history:
        for turn in history:
            messages.append({"role": turn['role'], "content": turn['text']})

    # Prepare user content
    if images:
        content = [{"type": "text", "text": prompt}]
        for img in images:
            import base64
            base64_image = base64.b64encode(img['data']).decode('utf-8')
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{img['mime_type']};base64,{base64_image}"
                }
            })
        messages.append({"role": "user", "content": content})
    else:
        # Simple text content for non-multimodal models (some might fail with list-style content)
        messages.append({"role": "user", "content": prompt})

    logger.info(f"Calling LiteLLM (model={model}). Payload: {len(prompt)} chars, {len(images or [])} images.")
    start_time = time.perf_counter()

    async def _call(api_key_override: str | None = None) -> str:
        """Inner call — optionally swap in a different API key."""
        if api_key_override:
            _apply_key(model, api_key_override)

        response = await litellm.acompletion(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        duration = time.perf_counter() - start_time
        logger.info(f"LiteLLM responded in {duration:.2f}s using {response.model}")

        usage = getattr(response, 'usage', None)
        if usage:
            logger.info(f"Usage: prompt_tokens={usage.prompt_tokens}, "
                        f"completion_tokens={usage.completion_tokens}, "
                        f"total_tokens={usage.total_tokens}")

        return response.choices[0].message.content

    try:
        return await _call()
    except litellm.RateLimitError as e:
        # Primary key hit rate limit — try secondary weak key if available
        is_weak_model = model == config.WEAK_MODEL
        secondary = config.WEAK_MODEL_API_KEY_2 if is_weak_model else None

        if secondary:
            logger.warning(f"Rate limit hit on primary key. Retrying with secondary key...")
            try:
                return await _call(api_key_override=secondary)
            except Exception as e2:
                logger.error(f"Secondary key also failed: {e2}")
                raise e2
        else:
            logger.error(f"Rate limit hit and no secondary key configured: {e}")
            raise
    except Exception as e:
        logger.error(f"Error calling LiteLLM: {str(e)}")
        raise
