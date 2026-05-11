import asyncio
import os
from dotenv import load_dotenv

from discord_client import DiscordWrapper
from utils import parse_discord_messages

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
        
        # Fetch recent messages so we have a real message ID to reply to
        raw_messages = await client.get_all_messages(CHANNEL_ID, limit=5)
        messages = parse_discord_messages(raw_messages)
        
        if messages:
            latest = messages[-1]  # newest message (list is oldest→newest)
            print(f"Replying to [{latest['id']}] {latest['author']}: {latest['content']!r}")
            
            await client.send_message(CHANNEL_ID, 'please 3')
        else:
            print('No messages found in channel.')
            
        await client.close()

    # Start the client
    await client.start(TOKEN)

if __name__ == '__main__':
    asyncio.run(main())