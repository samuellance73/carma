import logging
import sys
from src.utils import parse_discord_messages, parse_llm_response, format_transcript, typing_context
from src import llm_client
from src.prompts import get_system_prompt
import asyncio
from src import config
import os
import time
from src.discord_client import DiscordWrapper

# Configure logging
# We clear existing handlers to ensure our config takes precedence over discord.py
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger('bot')

# Silence verbose third-party loggers
logging.getLogger("discord").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# Fix for 10-second delay in httpx (common in Linux environments)
os.environ["HTTPX_IPV6"] = "0"




async def main():
    if not config.DISCORD_TOKEN or not config.CHANNEL_ID:
        logger.error("Missing DISCORD_TOKEN or DISCORD_CHANNEL_ID in config/env.")
        return

    client = DiscordWrapper()

    @client.event
    async def on_ready():
        await client.set_presence()
        logger.info(f"Bot logged in as {client.user}. Starting message processing...")
        start_event = time.perf_counter()
        
        raw_messages = await client.get_all_messages(config.CHANNEL_ID, limit=20)
        messages = parse_discord_messages(raw_messages)
        
        if messages:
            # Check for images in the most recent message
            last_raw_msg = raw_messages[0] # History is returned newest first by history()
            image_parts = []
            
            for attachment in last_raw_msg.attachments:
                if attachment.content_type and attachment.content_type.startswith('image/'):
                    logger.info(f"Downloading image: {attachment.filename}")
                    img_data = await attachment.read()
                    image_parts.append({
                        'data': img_data,
                        'mime_type': attachment.content_type
                    })


            transcript = format_transcript(messages)
            logger.info("--- LLM Transcript ---")
            logger.info(f"\n{transcript}")
            
            raw_reply = await llm_client.ask(transcript, images=image_parts, systemprompt=get_system_prompt())
            reply_params = parse_llm_response(raw_reply)
            
            if reply_params['content'] or reply_params['gif_query']:
                # Handle GIF search if requested
                gif_url = None
                if reply_params['gif_query']:
                    logger.info(f"Searching for GIF: {reply_params['gif_query']}")
                    gif_url = await client.search_discord_gifs(reply_params['gif_query'])
                
                # The wrapper now handles thinking time, splitting, typing, and GIFs!
                await client.send_message(
                    config.CHANNEL_ID, 
                    reply_params['content'], 
                    gif_url=gif_url,
                    reply_to_message_id=reply_params['reply'],
                    initial_delay_ms=reply_params['delay_ms']
                )
            else:
                logger.info("LLM decided not to reply.")
            
            logger.info(f"LLM Response: {reply_params}")
        else:
            logger.info('No messages found in channel.')
        
        total_time = time.perf_counter() - start_event
        logger.info(f"--- Processing complete in {total_time:.2f}s ---")
            
        await client.close()

    await client.start(config.DISCORD_TOKEN)

if __name__ == '__main__':
    asyncio.run(main())