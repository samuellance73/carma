import asyncio
import random
import logging
from src import config
from src import state
from src import image_cache
from src.brain import process_messages_and_reply

logger = logging.getLogger('listener')

def setup_events(client):
    """
    Attach event listeners to the Discord client.
    """
    
    @client.event
    async def on_ready():
        await client.set_presence()
        logger.info(f"Bot logged in as {client.user}. Listening for messages in channel {config.CHANNEL_ID}...")

        # Startup check: act as if we just noticed the channel after coming online
        delay = random.uniform(3.0, 8.0)
        logger.info(f"Doing startup check in {delay:.1f}s...")
        await asyncio.sleep(delay)

        async with state.processing_lock:
            try:
                await process_messages_and_reply(client)
            except Exception as e:
                logger.error(f"Error during startup check: {e}")

    @client.event
    async def on_message(message):
        # 1. Ignore our own messages
        if message.author == client.user:
            return
            
        # 2. Only process messages in the target channel
        if str(message.channel.id) != str(config.CHANNEL_ID):
            return

        # 3. Check if we are already processing a conversation
        if state.processing_lock.locked():
            logger.info("Already processing a message, ignoring new event to prevent duplication.")
            return

        # 4. Eagerly process any images in this message (runs alongside the delay)
        delay = random.uniform(3.0, 7.0)
        logger.info(f"Message received from {message.author.name}. Waiting {delay:.1f}s before processing...")

        await asyncio.gather(
            image_cache.process_message_images(message),
            asyncio.sleep(delay),
        )
        
        # 5. Acquire the lock and process
        async with state.processing_lock:
            try:
                await process_messages_and_reply(client)
            except Exception as e:
                logger.error(f"Error while processing messages: {e}")
