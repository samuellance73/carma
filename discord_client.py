import discord
import asyncio
import random
import config
from utils import calculate_typing_delay
from discord.http import Route

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
        messages = [msg async for msg in channel.history(limit=limit)]
        return messages

    async def search_discord_gifs(self, query: str) -> str | None:
        """Search Discord's internal GIF provider (no API key needed)."""
        try:
            # Discord's internal endpoint for GIF search
            data = await self.http.request(
                Route('GET', '/gifs/search'),
                params={'q': query, 'limit': 20, 'media_format': 'mp4'}
            )
            
            # The structure is a list of GIF objects
            if data and len(data) > 0:
                # Pick a random GIF from the first 8 results, but favor the top ones
                # min(rand, rand) effectively skews the distribution toward 0
                max_idx = min(len(data), 8)
                idx = min(random.randint(0, max_idx - 1), random.randint(0, max_idx - 1))
                return data[idx].get('url')
        except Exception as e:
            print(f"Internal GIF search failed: {e}")
        return None

    async def send_message(
        self,
        channel_id: int | str,
        content: str,
        *,
        gif_url: str | None = None,
        reply_to_message_id: int | str | None = None,
        initial_delay_ms: int = 0
    ) -> None:
        """
        Send a message, optionally as a reply. 
        Supports splitting by '|' for multi-message bursts with typing indicators.
        """
        # Ensure content is a string even if None was passed
        safe_content = content or ""
        bursts = [b.strip() for b in safe_content.split("|") if b.strip()]
        if not bursts and not gif_url:
            return

        channel = await self.fetch_channel(int(channel_id))

        # 1. Initial "reaction" delay with some jitter
        if initial_delay_ms > 0:
            # Add jitter to the LLM's requested delay from config
            jitter = random.uniform(*config.REACTION_JITTER_RANGE)
            actual_delay = (initial_delay_ms / 1000) * jitter
            await asyncio.sleep(actual_delay)

        # 2. Process each burst with its own typing delay
        for i, burst in enumerate(bursts):
            # Only the first part of a burst is a formal reply
            reply_to = reply_to_message_id if i == 0 else None
            
            # Occasional "human distraction" pause between bursts
            if i > 0 and random.random() < config.DISTRACTION_CHANCE:
                distraction_time = random.uniform(*config.DISTRACTION_TIME_RANGE)
                await asyncio.sleep(distraction_time)

            # Calculate human-like typing delay based on burst length
            delay = calculate_typing_delay(burst)
            
            # Show typing indicator while "typing" the burst
            async with channel.typing():
                await asyncio.sleep(delay)
            
            if reply_to is not None:
                try:
                    reference = await channel.fetch_message(int(reply_to))
                    await channel.send(burst, reference=reference)
                    print(f"Reply to {reply_to}: {burst}")
                except discord.NotFound:
                    await channel.send(burst)
                    print(f"Sent (fallback): {burst}")
            else:
                await channel.send(burst)
                print(f"Sent: {burst}")

        # 3. Send GIF if provided
        if gif_url:
            # Small human delay before sending the GIF
            await asyncio.sleep(random.uniform(1.0, 2.0))
            await channel.send(gif_url)
            print(f"Sent GIF: {gif_url}")
