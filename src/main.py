import asyncio
import config

from discord_client import DiscordWrapper
from utils import parse_discord_messages

async def main():
    if not config.DISCORD_TOKEN or not config.CHANNEL_ID:
        print("Missing DISCORD_TOKEN or DISCORD_CHANNEL_ID in config/env.")
        return

    client = DiscordWrapper()

    @client.event
    async def on_ready():
        print(f"Logged in as {client.user}")
        
        # Fetch recent messages so we have a real message ID to reply to
        raw_messages = await client.get_all_messages(config.CHANNEL_ID, limit=5)
        messages = parse_discord_messages(raw_messages)
        
        if messages:
            latest = messages[-1]  # newest message (list is oldest→newest)
            print(f"Replying to [{latest['id']}] {latest['author']}: {latest['content']!r}")
            
            await client.send_message(config.CHANNEL_ID, 'please 3')
        else:
            print('No messages found in channel.')
            
        await client.close()

    # Start the client
    await client.start(config.DISCORD_TOKEN)

if __name__ == '__main__':
    asyncio.run(main())