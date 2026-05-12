import logging
import time
from src.utils import parse_discord_messages, parse_llm_response, format_transcript
from src import llm_client
from src import config
from src.prompts import SYSTEM_PROMPT

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
        
        # Ask the LLM
        raw_reply = await llm_client.ask(transcript, images=image_parts, systemprompt=SYSTEM_PROMPT)
        reply_params = parse_llm_response(raw_reply)
        
        if reply_params['content'] or reply_params['gif_query']:
            # Handle GIF search if requested
            gif_url = None
            if reply_params['gif_query']:
                logger.info(f"Searching for GIF: {reply_params['gif_query']}")
                gif_url = await client.search_discord_gifs(reply_params['gif_query'])
            
            # Send the message using the client
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
