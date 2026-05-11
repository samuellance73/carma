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
        raw_messages = await client.get_all_messages(config.CHANNEL_ID, limit=10)
        messages = parse_discord_messages(raw_messages)
        
        if messages:
            system_prompt = """You are carma. You are a teenager but you're also smart and a bit shy.  You are a junior and are 17.
            And slightly bored. responses short. Sound very human. typos and misautocorrects often.  
            
You are in a Discord group chat. When given a new message, decide:
1. Whether to reply at all
2. What to say if you do
3. How long to "think" before sending.

You can split your response into multiple "bursts" using the '|' character to look more natural.
Example: "yo |how's it going? |i'm so bored lol"

ALWAYS respond with only valid JSON in this exact shape:
{
  "reply_id": "ID_HERE" | null,
  "message": "burst 1 | burst 2 | etc",
  "delay_ms": 2000
}"""
            transcript = format_transcript(messages)
            print("--- LLM Transcript ---")
            print(transcript)
            
            raw_reply = llm_client.ask(transcript, systemprompt=system_prompt)
            reply_params = parse_llm_response(raw_reply)
            
            if reply_params['content']:
                # Get the channel object for the typing indicator
                channel = await client.fetch_channel(int(config.CHANNEL_ID))
                
                # The wrapper now handles thinking time, splitting, and typing!
                await client.send_message(
                    config.CHANNEL_ID, 
                    reply_params['content'], 
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