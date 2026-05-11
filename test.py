from utils import parse_discord_messages, parse_llm_response
import llm_client
import os
import asyncio
from discord_client import DiscordWrapper
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = os.getenv('DISCORD_CHANNEL_ID')

async def main():
    if not TOKEN or not CHANNEL_ID:
        print("Missing DISCORD_TOKEN or DISCORD_CHANNEL_ID in environment variables.")
        return

    client = DiscordWrapper()

    @client.event
    async def on_ready():
        raw_messages = await client.get_all_messages(CHANNEL_ID, limit=5)
        messages = parse_discord_messages(raw_messages)
        
        if messages:
            system_prompt = """You are carma. You are a goofy teenager but you're also smart and a bit gay. And slightly bored. responses not too long.  
            
You are in a Discord group chat. When given a new message, decide:
1. Whether to reply at all
2. What to say if you do

ALWAYS respond with only valid JSON in this exact shape:
{
  "reply_id": "ID_HERE" | null,
  "message": "your message here or empty string if not replying",
  "delay_ms": 2000
}"""
            raw_reply = llm_client.ask(messages, systemprompt=system_prompt)
            reply_params = parse_llm_response(raw_reply)
            
            if reply_params['reply'] or reply_params['content']:
                if reply_params['delay_ms']:
                    await asyncio.sleep(reply_params['delay_ms'] / 1000)
                
                await client.send_message(
                    CHANNEL_ID, 
                    reply_params['content'], 
                    reply_to_message_id=reply_params['reply']
                )
            print(f"LLM Response: {reply_params}")
        if messages:
            print(messages)
        else:
            print('No messages found in channel to reply to.')
            
        await client.close()

    # Start the client
    await client.start(TOKEN)

if __name__ == '__main__':
    asyncio.run(main())