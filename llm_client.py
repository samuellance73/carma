import os
import logging
import json
import sys

from dotenv import load_dotenv
from google import genai
from google.genai import types

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger('llm_client')

load_dotenv()

# ── Configuration ─────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_MODEL   = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')

# ── Client ────────────────────────────────────────────────────────────────────
_client = genai.Client(api_key=GEMINI_API_KEY)

# ── Helpers ───────────────────────────────────────────────────────────────────
def _format_prompt(prompt: str | list[dict]) -> str:
    """Convert prompt to a clean transcript string if it's a list of message dicts."""
    if isinstance(prompt, str):
        return prompt
    
    if isinstance(prompt, list):
        formatted = []
        for msg in prompt:
            author = msg.get('author', 'Unknown')
            content = msg.get('content', '')
            msg_id = msg.get('id', 'UnknownID')
            reply_to = msg.get('reply_to')
            
            # Simple HH:MM timestamp
            time_str = ""
            if 'timestamp' in msg:
                try:
                    time_str = f"[{msg['timestamp'].split('T')[1][:5]}] "
                except:
                    pass

            reply_info = f" (replying to {reply_to})" if reply_to else ""
            formatted.append(f"{time_str}[{msg_id}]{reply_info} {author}: {content}")
            
        return "\n".join(formatted)
    
    return str(prompt)

# ── Core API function ─────────────────────────────────────────────────────────
def ask(
    prompt: str | list[dict],
    *,
    system: str | None = None,
    systemprompt: str | None = None,  # Alias used in bot.py
    history: list[dict] | None = None,
    model: str = GEMINI_MODEL,
    temperature: float = 1.0,
    max_tokens: int = 1024,
) -> str:
    """Send a prompt to Gemini and return the response text.

    Args:
        prompt:      The user message / question (string or list of dicts).
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

    formatted_prompt = _format_prompt(prompt)

    config = types.GenerateContentConfig(
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
    contents.append(
        types.Content(
            role='user',
            parts=[types.Part(text=formatted_prompt)],
        )
    )

    logger.info(f"Calling Gemini API (model={model}, temp={temperature})")
    if os.getenv('VERBOSE', 'false').lower() == 'true':
        logger.debug(f"Prompt: {formatted_prompt[:100]}...")
        if system_instruction:
            logger.debug(f"System: {system_instruction[:100]}...")

    try:
        response = _client.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )
        return response.text
    except Exception as e:
        logger.error(f"Error calling Gemini API: {str(e)}")
        logger.error(f"Request details: model={model}, config={config}")
        # Re-raise to let the caller handle it if needed, but we've logged it.
        raise
