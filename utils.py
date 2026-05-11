import json

def parse_discord_messages(messages) -> list[dict]:
    """
    Convert a list of discord.Message objects into an ordered (oldest → newest) list 
    of simplified message dicts.
    """
    if not messages:
        return []

    parsed = []
    for msg in messages:
        # Cut the fluff (edited, pinned, etc.) to keep tokens low and focus on dialogue
        parsed.append({
            'id': str(msg.id),
            'author': msg.author.display_name,
            'content': msg.content,
            'timestamp': msg.created_at.isoformat(),
            'reply_to': str(msg.reference.message_id) if msg.reference else None,
        })

    # Reverse so index 0 is the oldest
    parsed.reverse()
    return parsed

def parse_llm_response(raw_response: str, message_id: str = None) -> dict:
    """
    Takes the raw JSON string from the LLM and returns a structured dict for sending.
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
            "delay_ms": data.get("delay_ms", 0)
        }
    except Exception as e:
        import logging
        logging.error(f"Failed to parse LLM response as JSON: {e}")
        return {
            "content": "",
            "reply": None,
            "delay_ms": 0
        }
