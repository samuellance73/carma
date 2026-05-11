import utils
import llm_client
from discord_client import DiscordWrapper
import os
from dotenv import load_dotenv
import asyncio 

async def parse_test():
    load_dotenv()
    TOKEN = os.getenv('DISCORD_TOKEN')
    CHANNEL_ID = os.getenv('DISCORD_CHANNEL_ID')
    
    if not TOKEN or not CHANNEL_ID:
        print("Error: DISCORD_TOKEN or DISCORD_CHANNEL_ID not set in .env")
        return

    wrapper = DiscordWrapper()
    async with wrapper:
        await wrapper.login(TOKEN)
        raw_message = await wrapper.get_all_messages(CHANNEL_ID, limit=5)
        
        parsed = utils.parse_discord_messages(raw_message)
        
        print("\n" + "="*30)
        print("    LLM TRANSCRIPT VIEW")
        print("="*30)
        
        # Now we call the transcript formatter from utils
        transcript = utils.format_transcript(parsed)
        print(transcript)
        print("="*30 + "\n")

if __name__ == "__main__":
    asyncio.run(parse_test())