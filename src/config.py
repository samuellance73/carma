import os
from dotenv import load_dotenv

# Load .env file, ensuring it overrides existing environment variables
load_dotenv()

# ── Discord Configuration ───────────────────────────────────────────────────
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = os.getenv('DISCORD_CHANNEL_ID')

# ── Gemini Configuration ────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY') or os.getenv('LLM_IMAGE_API_KEY')
GEMINI_MODEL = os.getenv('GEMINI_MODEL') or os.getenv('LLM_IMAGE_MODEL', 'gemini-2.0-flash-exp')

# ── Behavior & Timing Settings ──────────────────────────────────────────────
# Chance of a random "distraction" pause between message bursts (0.0 to 1.0)
DISTRACTION_CHANCE = 0.15
DISTRACTION_TIME_RANGE = (0.5, 1.5)

# Typing speed (seconds per character)
TYPING_SPEED_RANGE = (0.04, 0.08)

# Minimum/Maximum "thinking" time at the start of a burst
BURST_THINKING_RANGE = (0.2, 0.8)

# Maximum delay for a single message burst
MAX_TYPING_DELAY = 4.0

# Jitter for the initial reaction delay requested by the LLM
REACTION_JITTER_RANGE = (0.85, 1.15)
