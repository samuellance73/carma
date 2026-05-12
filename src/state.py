"""
Manages the application's global state.
"""
import asyncio

# A lock to ensure we only process one conversation at a time.
# This prevents the bot from making 5 simultaneous LLM calls if 5 people message at once.
processing_lock = asyncio.Lock()

# Alternatively, a simple boolean flag
is_processing = False
