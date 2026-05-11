import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# ── Configuration ─────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_MODEL   = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')

# ── Client ────────────────────────────────────────────────────────────────────
_client = genai.Client(api_key=GEMINI_API_KEY)

# ── Core API function ─────────────────────────────────────────────────────────
def ask(
    prompt: str,
    *,
    system: str | None = None,
    history: list[dict] | None = None,
    model: str = GEMINI_MODEL,
    temperature: float = 1.0,
    max_tokens: int = 1024,
) -> str:
    """Send a prompt to Gemini and return the response text.

    Args:
        prompt:      The user message / question.
        system:      Optional system instruction to set model behaviour.
        history:     Optional prior conversation turns as a list of
                     ``{'role': 'user'|'model', 'text': '...'}`` dicts.
                     Each entry is converted to a ``types.Content`` object.
        model:       Gemini model ID (defaults to GEMINI_MODEL env var).
        temperature: Sampling temperature (0 = deterministic, 2 = creative).
        max_tokens:  Maximum output tokens.

    Returns:
        The model's response as a plain string.
    """
    config = types.GenerateContentConfig(
        temperature=temperature,
        max_output_tokens=max_tokens,
        system_instruction=system,
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
            parts=[types.Part(text=prompt)],
        )
    )

    response = _client.models.generate_content(
        model=model,
        contents=contents,
        config=config,
    )
    return response.text
