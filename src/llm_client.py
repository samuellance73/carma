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
if config.STRONG_MODEL_API_KEY:
    # If it's a gemini model, set GEMINI_API_KEY
    if "gemini" in (config.STRONG_MODEL or "").lower():
        os.environ["GEMINI_API_KEY"] = config.STRONG_MODEL_API_KEY
    # If it's a groq model, set GROQ_API_KEY
    elif "groq" in (config.STRONG_MODEL or "").lower():
        os.environ["GROQ_API_KEY"] = config.STRONG_MODEL_API_KEY

if config.WEAK_MODEL_API_KEY:
    if "gemini" in (config.WEAK_MODEL or "").lower():
        os.environ["GEMINI_API_KEY"] = config.WEAK_MODEL_API_KEY
    elif "groq" in (config.WEAK_MODEL or "").lower():
        os.environ["GROQ_API_KEY"] = config.WEAK_MODEL_API_KEY

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

    try:
        response = await litellm.acompletion(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        duration = time.perf_counter() - start_time
        logger.info(f"LiteLLM responded in {duration:.2f}s using {response.model}")
        
        # Log token usage
        usage = getattr(response, 'usage', None)
        if usage:
            logger.info(f"Usage: prompt_tokens={usage.prompt_tokens}, "
                        f"completion_tokens={usage.completion_tokens}, "
                        f"total_tokens={usage.total_tokens}")

        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error calling LiteLLM: {str(e)}")
        raise
