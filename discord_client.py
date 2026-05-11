import base64
import json
import os
import time

from curl_cffi import requests
from dotenv import load_dotenv

load_dotenv()

# ── Configuration ─────────────────────────────────────────────────────────────
TOKEN      = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = os.getenv('DISCORD_CHANNEL_ID')
GUILD_ID   = os.getenv('DISCORD_GUILD_ID', '@me')
BASE_URL   = 'https://discord.com'

# ── Chrome fingerprint ───────────────────────────────────────────────────────
# curl_cffi impersonates Chrome at the TLS/HTTP2 level (JA3, ALPN, header order).
# IMPERSONATE picks the closest available target; bump when curl_cffi adds 149.
_CHROME_FULL = '149.0.0.0'

IMPERSONATE  = 'chrome131'   # latest stable curl_cffi target (≈ Chrome 149)

USER_AGENT = (
    f'Mozilla/5.0 (X11; Linux x86_64) '
    f'AppleWebKit/537.36 (KHTML, like Gecko) '
    f'Chrome/{_CHROME_FULL} Safari/537.36'
)

LOCALE   = 'en-US'
TIMEZONE = 'America/New_York'
OS_NAME  = 'Linux'

# Discord client build number — update whenever Discord pushes a new build.
# Current value sourced from Discord's app.*.js in May 2026.
CLIENT_BUILD_NUMBER = 384235

# ── Shared session ────────────────────────────────────────────────────────────
# One session for the whole module — impersonation is applied to every request.
_session = requests.Session(impersonate=IMPERSONATE)

# ── x-super-properties ───────────────────────────────────────────────────────
# Mirrors the object Discord's web client serialises into this header.
_super_props = {
    "os":                          OS_NAME,
    "browser":                     "Chrome",
    "device":                      "",
    "system_locale":               LOCALE,
    "browser_user_agent":          USER_AGENT,
    "browser_version":             _CHROME_FULL,
    "os_version":                  "",
    "referrer":                    "",
    "referring_domain":            "",
    "referrer_current":            "",
    "referring_domain_current":    "",
    "release_channel":             "stable",
    "client_build_number":         CLIENT_BUILD_NUMBER,
    "client_event_source":         None,
    "design_id":                   0,
}
X_SUPER_PROPERTIES = base64.b64encode(
    json.dumps(_super_props, separators=(',', ':')).encode()
).decode()

# ── Nonce helper ──────────────────────────────────────────────────────────────
# Discord uses a Snowflake-style nonce: 64-bit int where the top 42 bits are
# a millisecond timestamp offset from the Discord epoch (2015-01-01).
_DISCORD_EPOCH_MS = 1420070400000

def _generate_nonce() -> str:
    """Return a Snowflake nonce string matching Discord's web client logic."""
    ms = int(time.time() * 1000)
    snowflake = (ms - _DISCORD_EPOCH_MS) << 22
    return str(snowflake)

# ── Headers factory ───────────────────────────────────────────────────────────
def get_headers(channel_id: str, *, is_post: bool = False) -> dict:
    """
    Return Discord-specific headers only.
    curl_cffi injects all browser-level headers (User-Agent, sec-ch-ua,
    sec-fetch-*, accept-encoding, connection, etc.) automatically via
    impersonation, so we must not duplicate them here.
    Pass is_post=True for POST / PATCH requests.
    """
    referer_path = f'/channels/{GUILD_ID}/{channel_id}'

    headers = {
        # ── Auth / Discord-specific ───────────────────────────────────────
        'authorization':        TOKEN,
        'x-super-properties':   X_SUPER_PROPERTIES,
        'x-discord-locale':     LOCALE,
        'x-discord-timezone':   TIMEZONE,
        'x-debug-options':      'bugReporterEnabled',

        # ── Request-scoped browser context ────────────────────────────────
        'origin':               BASE_URL,
        'referer':              f'{BASE_URL}{referer_path}',
    }

    if is_post:
        headers['content-type'] = 'application/json'

    return headers

# ── API helpers ───────────────────────────────────────────────────────────────
def send_message(
    channel_id: str,
    content: str,
    *,
    reply_to_message_id: str | None = None,
) -> None:
    """Send a message to *channel_id*.

    Args:
        channel_id:          Target channel snowflake ID.
        content:             Message text.
        reply_to_message_id: Snowflake ID of the message to reply to.
                             When supplied the message is sent as a Discord reply
                             (threads via ``message_reference``).
    """
    url  = f'{BASE_URL}/api/v9/channels/{channel_id}/messages'
    data: dict = {
        'content': content,
        'nonce':   _generate_nonce(),
        'tts':     False,
        'flags':   0,
    }

    if reply_to_message_id is not None:
        msg_ref: dict = {
            'message_id': reply_to_message_id,
            'channel_id': channel_id,
        }
        if GUILD_ID and GUILD_ID != '@me':
            msg_ref['guild_id'] = GUILD_ID   # only valid for server channels
        data['message_reference'] = msg_ref
        data['allowed_mentions'] = {
            'parse':        ['users', 'roles', 'everyone'],
            'replied_user': True,
        }

    res = _session.post(url, headers=get_headers(channel_id, is_post=True), json=data)
    if res.status_code in (200, 201):
        action = f'Reply to {reply_to_message_id}' if reply_to_message_id else 'Sent'
        print(f'{action}: {content}')
    else:
        print(f'Error {res.status_code}: {res.text}')

def get_all_messages(channel_id: str, limit: int = 50):
    """Fetch raw message objects from Discord (newest-first as returned by the API)."""
    url    = f'{BASE_URL}/api/v9/channels/{channel_id}/messages'
    params = {'limit': limit}
    res    = _session.get(url, headers=get_headers(channel_id), params=params)
    if res.status_code == 200:
        messages = res.json()
        print(f'Retrieved {len(messages)} messages')
        return messages
    else:
        print(f'Error {res.status_code}: {res.text}')
        return None

def parse_messages(channel_id: str, limit: int = 50) -> list[dict]:
    """
    Fetch and return an ordered (oldest → newest) list of simplified message dicts.

    Each entry contains:
        id          - message snowflake ID
        timestamp   - ISO-8601 timestamp (UTC)
        author      - display name (falls back to Username#discriminator)
        author_id   - user snowflake ID
        content     - message text
        attachments - list of attachment URLs (empty list if none)
        edited      - ISO-8601 timestamp if the message was edited, else None
        reply_to    - message ID being replied to, else None
        pinned      - bool
    """
    raw = get_all_messages(channel_id, limit)
    if not raw:
        return []

    parsed = []
    for msg in raw:
        author        = msg.get('author', {})
        username      = author.get('username', 'Unknown')
        discriminator = author.get('discriminator', '0')
        display_name  = (
            author.get('global_name') or
            (username if discriminator == '0' else f'{username}#{discriminator}')
        )

        ref = msg.get('message_reference')
        parsed.append({
            'id':          msg['id'],
            'timestamp':   msg['timestamp'],
            'author':      display_name,
            'author_id':   author.get('id'),
            'content':     msg.get('content', ''),
            'attachments': [a['url'] for a in msg.get('attachments', [])],
            'edited':      msg.get('edited_timestamp'),
            'reply_to':    ref.get('message_id') if ref else None,
            'pinned':      msg.get('pinned', False),
        })

    # Discord returns newest-first; reverse so index 0 is the oldest
    parsed.reverse()
    return parsed
