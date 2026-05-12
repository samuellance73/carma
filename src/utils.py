import json
import discord
import random
import re
import os
import logging
from src import config
from src import image_cache
from contextlib import asynccontextmanager

def parse_discord_messages(messages) -> list[dict]:
    """
    Convert a list of discord.Message objects into an ordered list of dicts.
    """
    if not messages:
        return []

    parsed = []
    VALID_TYPES = (discord.MessageType.default, discord.MessageType.reply)

    for msg in messages:
        if msg.type not in VALID_TYPES:
            continue
            
        attachments = []
        for attachment in msg.attachments:
            if attachment.content_type and attachment.content_type.startswith('image/'):
                attachments.append({
                    'id': str(attachment.id),
                    'url': attachment.url,
                    'content_type': attachment.content_type,
                    'filename': attachment.filename
                })

        parsed.append({
            'id': str(msg.id),
            'author': msg.author.display_name,
            'content': msg.content,
            'timestamp': msg.created_at.isoformat(),
            'reply_to': str(msg.reference.message_id) if msg.reference and msg.reference.message_id else None,
            'attachments': attachments
        })

    parsed.reverse()
    return parsed

def format_transcript(messages: list[dict]) -> str:
    """
    Converts a list of parsed message dicts into a clean text transcript for the LLM.
    """
    # Create a mapping for quick lookup of original messages (for quoting replies)
    msg_map = {str(m.get('id')): m for m in messages}
    
    formatted = []
    for msg in messages:
        author = msg.get('author', 'Unknown')
        content = msg.get('content', '')
        msg_id = msg.get('id', 'UnknownID')
        reply_to = msg.get('reply_to')
        
        # Replace 'Carma' with 'YOU' for clarity in the transcript
        if author.lower() == 'carma':
            author = 'YOU'
        
        # Replace 'carma' in content (case-insensitive)
        content = re.sub(r'(?i)\bcarma\b', 'YOU', content)
        
        time_str = ""
        if 'timestamp' in msg:
            try:
                time_str = f"[{msg['timestamp'].split('T')[1][:5]}] "
            except:
                pass

        attachments = msg.get('attachments', [])
        attachment_info = ""
        image_descriptions = []
        if attachments:
            filenames = [a['filename'] for a in attachments]
            attachment_info = f" (Attachments: {', '.join(filenames)})"
            # Inject cached image descriptions
            for a in attachments:
                desc = image_cache.get_description(a.get('id', ''))
                if desc:
                    image_descriptions.append(f"  [Image \"{a['filename']}\"]: {desc}")

        reply_info = ""
        if reply_to:
            orig_msg = msg_map.get(str(reply_to))
            if orig_msg:
                orig_author = orig_msg.get('author', 'Unknown')
                if orig_author.lower() == 'carma':
                    orig_author = 'YOU'
                
                orig_content = orig_msg.get('content', '')
                # Clean the quote as well
                orig_content = re.sub(r'(?i)\bcarma\b', 'YOU', orig_content)
                
                # Snippet if too long to keep transcript compact
                if len(orig_content) > 60:
                    orig_content = orig_content[:57] + "..."
                
                reply_info = f" (replying to {orig_author}: \"{orig_content}\")"
            else:
                # Fallback if original message is not in the provided history
                reply_info = f" (replying to {reply_to})"

        formatted.append(f"[{msg_id}] {time_str}{author}{reply_info}: {content}{attachment_info}")
        formatted.extend(image_descriptions)
        
    return "\n".join(formatted)

@asynccontextmanager
async def typing_context(channel):
    """
    A simple utility to show 'typing...' in a channel.
    Usage: async with utils.typing_context(channel): ...
    """
    async with channel.typing():
        yield

def calculate_typing_delay(text: str) -> float:
    """
    Calculate a natural-feeling typing delay in seconds based on message length.
    Simulates a casual typing speed with some randomness.
    """
    # Average characters per minute for a fast mobile typer
    char_delay = random.uniform(*config.TYPING_SPEED_RANGE)
    base_delay = len(text) * char_delay
    
    # Add a bit of "thinking" time at the start of a burst
    thinking_time = random.uniform(*config.BURST_THINKING_RANGE)
    
    return min(base_delay + thinking_time, config.MAX_TYPING_DELAY)

def parse_llm_response(raw_response: str, message_id: str = None) -> dict:
    """
    Takes the raw response from the LLM, extracts the JSON, and returns a structured dict.
    """
    logger = logging.getLogger('utils.parser')
    
    if not raw_response:
        logger.error("Received empty response from LLM.")
        return {
            "content": "",
            "reply": None,
            "delay_ms": 0,
            "gif_query": None,
            "reaction": None
        }

    clean_response = raw_response.strip()
    
    # 1. Try to find JSON inside code blocks if present
    import re
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", clean_response, re.DOTALL)
    if json_match:
        clean_response = json_match.group(1).strip()
    else:
        # 2. If no code blocks, try to find the first '{' and last '}'
        start = clean_response.find('{')
        end = clean_response.rfind('}')
        if start != -1 and end != -1 and end > start:
            clean_response = clean_response[start:end+1].strip()

    try:
        data = json.loads(clean_response)
        
        reply_target = data.get("reply_id")
        if not reply_target and data.get("reply") is True:
            reply_target = message_id
        
        return {
            "content": data.get("message", ""),
            "reply": str(reply_target) if reply_target else None,
            "delay_ms": data.get("delay_ms", 0),
            "gif_query": data.get("gif_query"),
            "reaction": data.get("reaction")
        }
    except Exception as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        logger.error(f"Raw response (first 500 chars): {raw_response[:500]}...")
        if len(raw_response) > 500:
             logger.error(f"Raw response (last 500 chars): ...{raw_response[-500:]}")
        
        return {
            "content": "",
            "reply": None,
            "delay_ms": 0,
            "gif_query": None,
            "reaction": None
        }
