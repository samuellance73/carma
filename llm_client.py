import logging
import json
import sys
import config

from google import genai
from google.genai import types

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger('llm_client')

# ── Client ────────────────────────────────────────────────────────────────────
_client = genai.Client(api_key=config.GEMINI_API_KEY)

# ── Core API function ─────────────────────────────────────────────────────────
def ask(
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

    config_params = types.GenerateContentConfig(
        temperature=temperature,
        max_output_tokens=max_tokens,
        system_instruction=system_instruction,
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

    logger.info(f"Calling Gemini API (model={model})")

    try:
        response = _client.models.generate_content(
            model=model,
            contents=contents,
            config=config_params,
        )
        return response.text
    except Exception as e:
        logger.error(f"Error calling Gemini API: {str(e)}")
        raise
