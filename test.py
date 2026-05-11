from discord_client import DiscordWrapper
import llm_client
import os
import asyncio
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
        print(f"Logged in as {client.user}")
        
        messages = await client.parse_messages(CHANNEL_ID, limit=5)
        print(llm_client.ask(messages))
        if messages:
            print(messages[-1]['content'])
        else:
            print('No messages found in channel to reply to.')
            
        await client.close()

    # Start the client
    await client.start(TOKEN)

if __name__ == '__main__':
    asyncio.run(main())