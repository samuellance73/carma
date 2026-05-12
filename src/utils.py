import json
import discord
import random
import config
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
    formatted = []
    for msg in messages:
        author = msg.get('author', 'Unknown')
        content = msg.get('content', '')
        msg_id = msg.get('id', 'UnknownID')
        reply_to = msg.get('reply_to')
        
        time_str = ""
        if 'timestamp' in msg:
            try:
                time_str = f"[{msg['timestamp'].split('T')[1][:5]}] "
            except:
                pass

        attachments = msg.get('attachments', [])
        attachment_info = ""
        if attachments:
            filenames = [a['filename'] for a in attachments]
            attachment_info = f" (Attachments: {', '.join(filenames)})"

        reply_info = f" (replying to {reply_to})" if reply_to else ""
        formatted.append(f"[{msg_id}] {time_str}{author}{reply_info}: {content}{attachment_info}")
        
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
    Takes the raw JSON string from the LLM and returns a structured dict.
    """
    try:
        clean_response = raw_response.strip()
        if clean_response.startswith("```"):
            lines = clean_response.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            clean_response = "\n".join(lines).strip()
        
        data = json.loads(clean_response)
        
        reply_target = data.get("reply_id")
        if not reply_target and data.get("reply") is True:
            reply_target = message_id
        
        return {
            "content": data.get("message", ""),
            "reply": reply_target,
            "delay_ms": data.get("delay_ms", 0),
            "gif_query": data.get("gif_query")
        }
    except Exception as e:
        import logging
        logging.error(f"Failed to parse LLM response as JSON: {e}")
        return {
            "content": "",
            "reply": None,
            "delay_ms": 0
        }
