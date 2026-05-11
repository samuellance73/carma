from dotenv import load_dotenv
import os
import llm_client
import discord_client

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = os.getenv('DISCORD_CHANNEL_ID')
GUILD_ID = os.getenv('DISCORD_GUILD_ID')

messages = discord_client.parse_messages(CHANNEL_ID, limit=5)

ai_reply = llm_client.ask(prompt="You are a pirate. Make your response very short.",)

discord_client.send_message(CHANNEL_ID, ai_reply, reply_to_message_id=messages[-1]['id'])
