import discord
import os

class DiscordWrapper(discord.Client):
    """
    A wrapper around discord.py-self providing helper methods for fetching
    and sending messages.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def get_all_messages(self, channel_id: int | str, limit: int = 50):
        """Fetch message objects from Discord."""
        channel = await self.fetch_channel(int(channel_id))
        # discord.py-self history returns newest-first by default
        messages = [msg async for msg in channel.history(limit=limit)]
        return messages

    async def send_message(
        self,
        channel_id: int | str,
        content: str,
        *,
        reply_to_message_id: int | str | None = None,
    ) -> None:
        """Send a message, optionally as a reply to an existing message."""
        channel = await self.fetch_channel(int(channel_id))
        
        if reply_to_message_id is not None:
            try:
                reference = await channel.fetch_message(int(reply_to_message_id))
                await channel.send(content, reference=reference)
                print(f"Reply to {reply_to_message_id}: {content}")
                return
            except discord.NotFound:
                print(f"Message {reply_to_message_id} not found, sending as normal message.")
        
        await channel.send(content)
        print(f"Sent: {content}")
