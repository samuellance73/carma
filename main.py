import json

from discord_client import CHANNEL_ID, send_message, parse_messages

# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    # Fetch recent messages so we have a real message ID to reply to
    messages = parse_messages(CHANNEL_ID, limit=5)
    if messages:
        latest = messages[-1]  # newest message (list is oldest→newest)
        print(f"Replying to [{latest['id']}] {latest['author']}: {latest['content']!r}")
       # send_message(CHANNEL_ID, 'please 2', reply_to_message_id=latest['id'])

        send_message(CHANNEL_ID, 'please 3')
    else:
        print('No messages found in channel.')