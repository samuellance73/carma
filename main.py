import asyncio
import logging
import sys
import os
from src import config
from src.client import DiscordWrapper
from src.listener import setup_events

def setup_logging():
    # Clear existing handlers to ensure our config takes precedence over discord.py
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stderr
    )

    # Silence verbose third-party loggers
    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

async def main():
    setup_logging()
    
    # Fix for 10-second delay in httpx (common in Linux environments)
    os.environ["HTTPX_IPV6"] = "0"
    
    logger = logging.getLogger('main')
    
    if not config.DISCORD_TOKEN or not config.CHANNEL_ID:
        logger.error("Missing DISCORD_TOKEN or DISCORD_CHANNEL_ID in config/env.")
        return

    # Initialize the client
    client = DiscordWrapper()
    
    # Attach the event listeners (on_ready, on_message)
    setup_events(client)
    
    # Start the bot (this runs forever until stopped)
    try:
        await client.start(config.DISCORD_TOKEN)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")

if __name__ == '__main__':
    asyncio.run(main())
