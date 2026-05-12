import os
from dotenv import load_dotenv

# Load .env file, ensuring it overrides existing environment variables
load_dotenv(override=True)

# ── Discord Configuration ───────────────────────────────────────────────────
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = os.getenv('DISCORD_CHANNEL_ID')

# ── LLM Configuration ───────────────────────────────────────────────────────
# "Strong" model: Image-capable, multimodal (Gemini)
STRONG_MODEL = os.getenv('LLM_STRONG_MODEL')
_strong_key_env = os.getenv('LLM_STRONG_API_KEYS') or os.getenv('LL_STRONG_API_KEY') or os.getenv('LLM_STRONG_API_KEY') or ""
STRONG_MODEL_API_KEYS = [k.strip() for k in _strong_key_env.split(',') if k.strip()]

# "Weak" model: Fast, text-only (Groq)
WEAK_MODEL = os.getenv('LLM_WEAK_MODEL')
_weak_key_env = os.getenv('LLM_WEAK_API_KEYS') or os.getenv('LLM_WEAK_API_KEY') or ""
WEAK_MODEL_API_KEYS = [k.strip() for k in _weak_key_env.split(',') if k.strip()]
# Fallback if primary is rate-limited (legacy support)
_weak_key_2 = os.getenv('LLM_WEAK_API_KEY_2')
if _weak_key_2 and _weak_key_2.strip() not in WEAK_MODEL_API_KEYS:
    WEAK_MODEL_API_KEYS.append(_weak_key_2.strip())

# ── Behavior & Timing Settings ──────────────────────────────────────────────
DISTRACTION_CHANCE = 0.15
DISTRACTION_TIME_RANGE = (0.5, 1.5)
TYPING_SPEED_RANGE = (0.04, 0.08)
BURST_THINKING_RANGE = (0.2, 0.8)
MAX_TYPING_DELAY = 4.0
REACTION_JITTER_RANGE = (0.85, 1.15)
