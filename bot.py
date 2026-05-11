from utils import parse_discord_messages, parse_llm_response, format_transcript, typing_context
import llm_client
import asyncio
import config
from discord_client import DiscordWrapper

async def main():
    if not config.DISCORD_TOKEN or not config.CHANNEL_ID:
        print("Missing DISCORD_TOKEN or DISCORD_CHANNEL_ID in config/env.")
        return

    client = DiscordWrapper()

    @client.event
    async def on_ready():
        raw_messages = await client.get_all_messages(config.CHANNEL_ID, limit=15)
        messages = parse_discord_messages(raw_messages)
        
        if messages:
            # Check for images in the most recent message
            last_raw_msg = raw_messages[0] # History is returned newest first by history()
            image_parts = []
            
            for attachment in last_raw_msg.attachments:
                if attachment.content_type and attachment.content_type.startswith('image/'):
                    print(f"Downloading image: {attachment.filename}")
                    img_data = await attachment.read()
                    image_parts.append({
                        'data': img_data,
                        'mime_type': attachment.content_type
                    })

            system_prompt = """You are carma. You are a teenager but you're also smart and a bit shy.  You are a junior and are 17.
            And slightly bored but still somewhat funny. responses short. Sound very human. typos and misautocorrects often.  If even slightly obvious, who you are replying to, the ID doesn't need to be specified and put null. 
            
You are in a Discord group chat. When given a new message, decide:
1. Whether to reply at all
2. What to say if you do (Choose EITHER a text message OR a GIF search, not both)
3. How long to "think" before sending.

You can split your response into multiple "bursts" using the '|' character to look more natural. But don't overuse it..
Example: "yo |how's it going? |i'm so bored lol"

ALWAYS respond with only valid JSON in this exact shape. If you send a gif_query, the message should be null or empty:
{
  "reply_id": "ID_HERE" | null,
  "message": "text content" | null,
  "gif_query": "search term" | null,
  "delay_ms": 2000
}"""
            transcript = format_transcript(messages)
            print("--- LLM Transcript ---")
            print(transcript)
            
            raw_reply = llm_client.ask(transcript, images=image_parts, systemprompt=system_prompt)
            reply_params = parse_llm_response(raw_reply)
            
            if reply_params['content'] or reply_params['gif_query']:
                # Handle GIF search if requested
                gif_url = None
                if reply_params['gif_query']:
                    print(f"Searching for GIF: {reply_params['gif_query']}")
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
                print("LLM decided not to reply.")
            
            print(f"LLM Response: {reply_params}")
        else:
            print('No messages found in channel.')
            
        await client.close()

    await client.start(config.DISCORD_TOKEN)

if __name__ == '__main__':
    asyncio.run(main())