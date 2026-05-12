import logging
import time
from src.utils import parse_discord_messages, parse_llm_response, format_transcript
from src import llm_client
from src import config
from src import image_cache
from src.prompts import get_system_prompt

logger = logging.getLogger('brain')

async def process_messages_and_reply(client):
    """
    Core logic to fetch context, call LLM, and send a reply.
    """
    start_event = time.perf_counter()
    
    # Fetch the last 20 messages for context
    raw_messages = await client.get_all_messages(config.CHANNEL_ID, limit=20)
    messages = parse_discord_messages(raw_messages)
    
    if messages:
        # Describe any images in the message window (skips already-cached ones)
        await image_cache.process_bulk_images(raw_messages)

        transcript = format_transcript(messages)
        logger.info("--- LLM Transcript ---")
        logger.info(f"\n{transcript}")
        
        # Ask the LLM (always text-only; image descriptions are in the transcript)
        raw_reply = await llm_client.ask(transcript, systemprompt=get_system_prompt())
        reply_params = parse_llm_response(raw_reply)
        
        if reply_params['content'] or reply_params['gif_query'] or reply_params['reaction']:
            # Handle emoji reaction if requested
            if reply_params['reaction']:
                react_target = reply_params['reply'] or messages[-1]['id']
                await client.add_reaction(config.CHANNEL_ID, react_target, reply_params['reaction'])

            # Handle GIF search if requested
            gif_url = None
            if reply_params['gif_query']:
                logger.info(f"Searching for GIF: {reply_params['gif_query']}")
                gif_url = await client.search_discord_gifs(reply_params['gif_query'])
            
            # Send the message using the client (only if there's text/gif to send)
            if reply_params['content'] or gif_url:
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
