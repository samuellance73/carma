import asyncio
import os
from dotenv import load_dotenv

import llm_client
from discord_client import DiscordWrapper
from utils import parse_discord_messages

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = os.getenv('DISCORD_CHANNEL_ID')
GUILD_ID = os.getenv('DISCORD_GUILD_ID')

async def main():
    if not TOKEN or not CHANNEL_ID:
        print("Missing DISCORD_TOKEN or DISCORD_CHANNEL_ID in environment variables.")
        return

    client = DiscordWrapper()

    @client.event
    async def on_ready():
        print(f"Logged in as {client.user}")
        
        raw_messages = await client.get_all_messages(CHANNEL_ID, limit=5)
        messages = parse_discord_messages(raw_messages)
        
        if messages:
            ai_reply = llm_client.ask(messages,systemprompt="you are a teenager. make your reply very short. but kind of smart.")
            await client.send_message(
                CHANNEL_ID, 
                ai_reply, 
                reply_to_message_id=messages[-1]['id']
            )
        else:
            print('No messages found in channel to reply to.')
            
        await client.close()

    # Start the client
    await client.start(TOKEN)

if __name__ == '__main__':
    asyncio.run(main())
