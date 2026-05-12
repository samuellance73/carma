"""
Image description cache.

When a Discord message contains an image, we send it to the strong (multimodal)
model with a neutral "describe everything" prompt. The resulting text description
is cached by attachment ID so it only needs to be generated once.

The cached descriptions are later injected into the text transcript so the
conversational (weak) model can reason about images without needing vision.
"""

import logging
import time
import asyncio
from src import llm_client, config

logger = logging.getLogger('image_cache')

# In-memory cache: { attachment_id: { "description": str, "timestamp": float } }
_cache: dict[str, dict] = {}

CACHE_TTL = 1800       # 30 minutes
MAX_CACHE_SIZE = 50

# File extensions we treat as images (fallback when content_type is None)
_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff', '.svg'}

VISION_PROMPT = (
    "Describe this image in detail. "
    "Be extensive. List everything about the image in any way. All information on the image. THE DESCRIPTION SHOULD BE BETTER THAN IF A PERSON SAW THE IMAGE.  "
    "Write in plain language — this description. One-Two paragraph long. ANY TEXT in the image must be extracted."
    "will be used by someone who cannot see the image."
)


def _is_image_attachment(att) -> bool:
    """Check if an attachment is an image via content_type OR file extension."""
    # Primary: check content_type
    if att.content_type and att.content_type.startswith('image/'):
        return True
    # Fallback: check file extension (content_type is often None in history)
    if att.filename:
        import os
        ext = os.path.splitext(att.filename)[1].lower()
        if ext in _IMAGE_EXTENSIONS:
            logger.info(
                f"  content_type is '{att.content_type}' but extension '{ext}' "
                f"looks like an image — treating as image"
            )
            return True
    return False


def _get_mime_type(att) -> str:
    """Get the MIME type for an attachment, with fallback based on extension."""
    if att.content_type:
        return att.content_type
    # Guess from extension
    ext_map = {
        '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
        '.gif': 'image/gif', '.webp': 'image/webp', '.bmp': 'image/bmp',
        '.tiff': 'image/tiff', '.svg': 'image/svg+xml',
    }
    if att.filename:
        import os
        ext = os.path.splitext(att.filename)[1].lower()
        return ext_map.get(ext, 'image/png')
    return 'image/png'


# ── Public API ────────────────────────────────────────────────────────────────

async def describe_image(attachment) -> str | None:
    """
    Process a single Discord attachment through the strong model.
    Returns the cached (or freshly generated) description, or None on failure.
    """
    att_id = str(attachment.id)

    # Cache hit
    if att_id in _cache:
        logger.info(f"Image cache HIT: {attachment.filename} (id={att_id})")
        return _cache[att_id]["description"]

    # Only handle images
    if not _is_image_attachment(attachment):
        logger.info(f"  not an image, skipping: {attachment.filename} (content_type={attachment.content_type})")
        return None

    mime = _get_mime_type(attachment)

    try:
        logger.info(f">>> Describing image via strong model ({config.STRONG_MODEL}): {attachment.filename} (id={att_id}, mime={mime})")
        img_data = await attachment.read()
        logger.info(f"    Downloaded {len(img_data)} bytes")

        description = await llm_client.ask(
            VISION_PROMPT,
            images=[{"data": img_data, "mime_type": mime}],
            model=config.STRONG_MODEL,
            temperature=0.3,
            max_tokens=512,
        )

        logger.info(f"    Strong model returned {len(description)} chars")

        _evict()

        _cache[att_id] = {
            "description": description.strip(),
            "timestamp": time.time(),
        }

        logger.info(
            f"    CACHED description for {attachment.filename} (id={att_id}):\n"
            f"    {description.strip()}"
        )
        logger.info(f"    Cache now has {len(_cache)} entries: {list(_cache.keys())}")
        return description.strip()

    except Exception as e:
        logger.error(f"!!! FAILED to describe image {attachment.filename} (id={att_id}): {e}", exc_info=True)
        return None


async def process_message_images(message) -> None:
    """Process all image attachments in a single Discord message."""
    logger.info(
        f"process_message_images: message from {message.author.display_name}, "
        f"{len(message.attachments)} attachment(s)"
    )
    tasks = []
    for att in message.attachments:
        logger.info(
            f"  attachment: {att.filename} | content_type={att.content_type} | id={att.id}"
        )
        if _is_image_attachment(att):
            tasks.append(describe_image(att))
        else:
            logger.info(f"  skipping (not an image): {att.filename}")
    if tasks:
        logger.info(f"  processing {len(tasks)} image(s)...")
        await asyncio.gather(*tasks)
    else:
        logger.info("  no images to process.")


async def process_bulk_images(messages) -> None:
    """
    Process images from a list of raw Discord messages (e.g. on startup).
    Already-cached images are skipped automatically.
    """
    logger.info(f"process_bulk_images: scanning {len(messages)} messages for images (newest first)...")
    tasks = []
    # Process newest messages first so the most recent images are ready soonest
    for msg in messages:  # messages from history() are already newest-first
        for att in msg.attachments:
            logger.info(
                f"  found attachment in msg {msg.id} by {msg.author.display_name}: "
                f"{att.filename} | content_type={att.content_type} | id={att.id}"
            )
            if _is_image_attachment(att):
                tasks.append(describe_image(att))
            else:
                logger.info(f"  skipping (not an image): {att.filename}")

    if tasks:
        logger.info(f"Bulk processing {len(tasks)} image(s) from message history...")
        await asyncio.gather(*tasks)
        logger.info(f"Bulk image processing complete. Cache state: {list(_cache.keys())}")
    else:
        logger.info("No images found in message history.")


def get_description(attachment_id: str) -> str | None:
    """Look up a cached description by attachment ID."""
    entry = _cache.get(str(attachment_id))
    if entry:
        logger.debug(f"get_description HIT for id={attachment_id}")
        return entry["description"]
    logger.warning(f"get_description MISS for id={attachment_id} (cache has: {list(_cache.keys())})")
    return None


# ── Internals ─────────────────────────────────────────────────────────────────

def _evict():
    """Remove expired entries and enforce size limit."""
    now = time.time()

    # Drop anything older than TTL
    expired = [k for k, v in _cache.items() if now - v["timestamp"] > CACHE_TTL]
    for k in expired:
        del _cache[k]

    # If still over capacity, drop the oldest entries
    while len(_cache) >= MAX_CACHE_SIZE:
        oldest = min(_cache, key=lambda k: _cache[k]["timestamp"])
        del _cache[oldest]
