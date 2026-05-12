import discord
import asyncio
import random
import logging
from src import config
from src.utils import calculate_typing_delay
from discord.http import Route

logger = logging.getLogger('discord_client')

class DiscordWrapper(discord.Client):
    """
    A wrapper around discord.py-self providing helper methods for fetching
    and sending messages.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def set_presence(self):
        # Create the 'Playing' activity
        activity = discord.Game(name="Roblox")
        
        # Apply the activity and set status to 'online'
        await self.change_presence(status=discord.Status.online, activity=activity)
        
        logger.info(f"Logged in as {self.user} and set status to Playing Roblox")

    async def get_all_messages(self, channel_id: int | str, limit: int = 50):
        """Fetch message objects from Discord."""
        channel = await self.fetch_channel(int(channel_id))
        messages = [msg async for msg in channel.history(limit=limit)]
        return messages

    async def add_reaction(self, channel_id: int | str, message_id: int | str, emoji: str) -> None:
        """Add an emoji reaction to a specific message."""
        try:
            channel = await self.fetch_channel(int(channel_id))
            message = await channel.fetch_message(int(message_id))
            await message.add_reaction(emoji)
            logger.info(f"Reacted with {emoji} to message {message_id}")
        except Exception as e:
            logger.warning(f"Failed to add reaction '{emoji}' to message {message_id}: {e}")

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
                logger.info(f"GIF search for '{query}' returned {len(data)} results.")
                # Pick a random GIF from the first 5 results, but favor the top ones
                max_idx = min(len(data), 5)
                idx = min(random.randint(0, max_idx - 1), random.randint(0, max_idx - 1))
                
                gif_data = data[idx]
                # Try common URL fields
                url = gif_data.get('url') or gif_data.get('proxy_url') or gif_data.get('gif_url')
                if url:
                    return url
                else:
                    logger.warning(f"GIF result at index {idx} has no known URL field. Data: {gif_data}")
            else:
                logger.info(f"GIF search for '{query}' returned no results.")
        except Exception as e:
            logger.error(f"Internal GIF search failed: {e}")
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
                    # Ensure it's a numeric ID before trying to fetch
                    if str(reply_to).isdigit():
                        reference = await channel.fetch_message(int(reply_to))
                        await channel.send(burst, reference=reference)
                        logger.info(f"Reply to {reply_to}: {burst}")
                    else:
                        logger.warning(f"Invalid reply_to ID: {reply_to}. Sending as normal message.")
                        await channel.send(burst)
                except (discord.NotFound, ValueError, TypeError) as e:
                    logger.warning(f"Could not reply to {reply_to} ({e}). Sending as normal message.")
                    await channel.send(burst)
            else:
                await channel.send(burst)
                logger.info(f"Sent: {burst}")

        # 3. Send GIF if provided
        if gif_url:
            # Small human delay before sending the GIF
            await asyncio.sleep(random.uniform(1.0, 2.0))
            
            # If we haven't sent any text, this GIF might need to be the reply
            if not bursts and reply_to_message_id:
                try:
                    if str(reply_to_message_id).isdigit():
                        reference = await channel.fetch_message(int(reply_to_message_id))
                        await channel.send(gif_url, reference=reference)
                        logger.info(f"Sent GIF as reply to {reply_to_message_id}: {gif_url}")
                        return
                except Exception as e:
                    logger.warning(f"Could not reply with GIF: {e}")

            await channel.send(gif_url)
            logger.info(f"Sent GIF: {gif_url}")
