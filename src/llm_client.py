import logging
import json
import sys
import time
from src import config

from google import genai
from google.genai import types

logger = logging.getLogger('llm_client')
logging.getLogger("httpx").setLevel(logging.WARNING)

# ── Client ────────────────────────────────────────────────────────────────────
_client = genai.Client(api_key=config.GEMINI_API_KEY)

# ── Core API function ─────────────────────────────────────────────────────────
async def ask(
    prompt: str,
    *,
    images: list[dict] | None = None,
    system: str | None = None,
    systemprompt: str | None = None,
    history: list[dict] | None = None,
    model: str = config.GEMINI_MODEL,
    temperature: float = 1.0,
    max_tokens: int = 1024,
) -> str:
    """Send a text prompt and optional images to Gemini and return the response text.

    Args:
        prompt:      The text message / transcript to send.
        images:      Optional list of dicts with 'data' (bytes) and 'mime_type'.
        system:      Optional system instruction to set model behaviour.
        systemprompt: Alias for 'system'.
        history:     Optional prior conversation turns.
        model:       Gemini model ID.
        temperature: Sampling temperature.
        max_tokens:  Maximum output tokens.

    Returns:
        The model's response as a plain string.
    """
    # Handle aliases
    system_instruction = system or systemprompt

    # Disable AFC (Automatic Function Calling) to avoid unnecessary overhead and potential delays
    config_params = types.GenerateContentConfig(
        temperature=temperature,
        max_output_tokens=max_tokens,
        system_instruction=system_instruction,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
    )

    # Build the contents list from optional history + current prompt
    contents: list[types.Content] = []
    for turn in (history or []):
        contents.append(
            types.Content(
                role=turn['role'],
                parts=[types.Part(text=turn['text'])],
            )
        )
    
    # Current turn
    parts = [types.Part(text=prompt)]
    if images:
        for img in images:
            parts.append(
                types.Part(
                    inline_data=types.Blob(
                        data=img['data'],
                        mime_type=img['mime_type']
                    )
                )
            )

    contents.append(
        types.Content(
            role='user',
            parts=parts,
        )
    )

    logger.info(f"Calling Gemini API (model={model}). Payload: {len(prompt)} chars, {len(images or [])} images.")
    start_time = time.perf_counter()

    try:
        # Use the async client (.aio) to avoid blocking the event loop
        response = await _client.aio.models.generate_content(
            model=model,
            contents=contents,
            config=config_params,
        )
        duration = time.perf_counter() - start_time
        logger.info(f"Gemini API responded in {duration:.2f}s")
        
        # Log token usage if available
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            logger.info(f"Usage: prompt_tokens={response.usage_metadata.prompt_token_count}, "
                        f"candidates_tokens={response.usage_metadata.candidates_token_count}, "
                        f"total_tokens={response.usage_metadata.total_token_count}")
            
        return response.text
    except Exception as e:
        logger.error(f"Error calling Gemini API: {str(e)}")
        raise
