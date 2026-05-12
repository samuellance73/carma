import logging
import json
import os
import time
import litellm
from src import config

# Set up logging for this module
logger = logging.getLogger('llm_client')

# Configure LiteLLM logging
os.environ['LITELLM_LOG'] = 'INFO'
logging.getLogger("litellm").setLevel(logging.WARNING)

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

def _mask_key(api_key: str | None) -> str:
    """Mask the API key for safe logging."""
    if not api_key:
        return "None"
    if len(api_key) <= 8:
        return "***"
    return f"{api_key[:6]}...{api_key[-4:]}"

if config.STRONG_MODEL_API_KEYS:
    logger.info(f"Initialized STRONG model with {len(config.STRONG_MODEL_API_KEYS)} keys. Primary: {_mask_key(config.STRONG_MODEL_API_KEYS[0])}")
    _apply_key(config.STRONG_MODEL, config.STRONG_MODEL_API_KEYS[0])
if config.WEAK_MODEL_API_KEYS:
    logger.info(f"Initialized WEAK model with {len(config.WEAK_MODEL_API_KEYS)} keys. Primary: {_mask_key(config.WEAK_MODEL_API_KEYS[0])}")
    _apply_key(config.WEAK_MODEL, config.WEAK_MODEL_API_KEYS[0])

async def ask(
    prompt: str,
    *,
    images: list[dict] | None = None,
    system: str | None = None,
    systemprompt: str | None = None,
    history: list[dict] | None = None,
    model: str | None = None,
    temperature: float = 1.0,
    max_tokens: int = 2048,
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
            logger.info(f"Applying API key {_mask_key(api_key_override)} for {model}")
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

    keys_to_try = config.STRONG_MODEL_API_KEYS if model == config.STRONG_MODEL else config.WEAK_MODEL_API_KEYS
    if not keys_to_try:
        keys_to_try = [None] # Try with whatever is in environment

    for attempt, key in enumerate(keys_to_try):
        try:
            logger.info(f"Attempt {attempt + 1}/{len(keys_to_try)}: Making request with key {_mask_key(key)}")
            return await _call(api_key_override=key)
        except litellm.RateLimitError as e:
            if attempt < len(keys_to_try) - 1:
                next_key = keys_to_try[attempt + 1]
                logger.warning(f"Rate limit hit on key {_mask_key(key)} (Attempt {attempt + 1}). Swapping to next key: {_mask_key(next_key)}...")
                continue
            else:
                logger.error(f"Rate limit hit on ALL {len(keys_to_try)} keys! Last key tried: {_mask_key(key)}. Error: {e}")
                raise
        except Exception as e:
            logger.error(f"Error calling LiteLLM: {str(e)}")
            raise
