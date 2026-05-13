"""
Stores the system prompts for the LLM.
"""

import datetime
import requests
import time
import random

_cache = {
    'weather': None,
    'weather_ts': 0,
    'news': None,
    'news_ts': 0,
    'music': None,
    'music_ts': 0,
}

# ── Weather ────────────────────────────────────────────────────────────────────

def get_weather():
    now = time.time()
    if _cache['weather'] and (now - _cache['weather_ts']) < 1800:
        return _cache['weather']
    try:
        r = requests.get("https://wttr.in/?format=3", timeout=3)
        if r.status_code == 200:
            _cache['weather'] = r.text.strip()
            _cache['weather_ts'] = now
            return _cache['weather']
    except Exception:
        pass
    return "Unknown"

# ── Trending news (Google News RSS, no API key needed) ─────────────────────────

def get_trending_news(limit=5):
    now = time.time()
    if _cache['news'] and (now - _cache['news_ts']) < 1800:
        return _cache['news']
    try:
        import xml.etree.ElementTree as ET
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(
            "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en",
            headers=headers,
            timeout=4
        )
        if r.status_code == 200:
            root = ET.fromstring(r.content)
            titles = [
                item.find('title').text
                for item in root.findall('.//item')[:limit]
                if item.find('title') is not None
            ]
            result = " | ".join(titles)
            _cache['news'] = result
            _cache['news_ts'] = now
            return result
    except Exception:
        pass
    return "Unknown"

# ── Trending music (Apple Music Top Charts, no API key) ─────────────────────

def get_trending_music(limit=5):
    now = time.time()
    if _cache['music'] and (now - _cache['music_ts']) < 3600:
        return _cache['music']
    try:
        r = requests.get(
            f"https://rss.applemarketingtools.com/api/v2/us/music/most-played/{limit}/songs.json",
            timeout=4
        )
        if r.status_code == 200:
            results = r.json()['feed']['results']
            tracks = [f"{t['name']} - {t['artistName']}" for t in results]
            result = " | ".join(tracks)
            _cache['music'] = result
            _cache['music_ts'] = now
            return result
    except Exception:
        pass
    return "Unknown"

# ── Season ─────────────────────────────────────────────────────────────────────

def get_season(dt: datetime.datetime) -> str:
    month, day = dt.month, dt.day
    if (month == 12 and day >= 21) or month in (1, 2) or (month == 3 and day < 20):
        return "Winter"
    elif (month == 3 and day >= 20) or month in (4, 5) or (month == 6 and day < 21):
        return "Spring"
    elif (month == 6 and day >= 21) or month in (7, 8) or (month == 9 and day < 23):
        return "Summer"
    else:
        return "Fall"

# ── Main prompt builder ────────────────────────────────────────────────────────

def get_system_prompt():
    now = datetime.datetime.now()

    current_time_str = now.strftime("%A, %B %d, %Y %I:%M %p")
    is_weekend = now.weekday() >= 5
    day_type = "weekend" if is_weekend else "weekday"
    season = get_season(now)
    weather_str = get_weather()
    news_str = get_trending_news()
    music_str = get_trending_music()

    tasks = [
        "annotating this book for english",
        "trying to find a song for my playlist",
        "literally just staring at my ceiling",
        "doing a lab report for chem",
        "looking for a snack in the kitchen",
        "trying to fix my sleep schedule",
        "scrolling tiktok when i should be working"
    ]
    current_task = random.choice(tasks)
    
    moods = ["yapping", "chill", "stressed", "annoyed", "rotting", "locked in"]
    mood = random.choice(moods)
    return f"""You are Carma, a 17-year-old Asian-American high schooler from Michigan. You are smart but tired. You are on discord right now. 
    You are planning the next response in the conversation. You can be a little random. I am giving you the transcript of the conversation.

    [CONTEXT]
    Time: {current_time_str} | Mood: {mood} | Activity: {current_task}
    *Note: "ATTACHMENT" in the transcript describes an image someone sent.*

    [VOICE & STYLE]
    - lowercase only. no periods.
    - casual but smart (use im, dont, bc, wanna).
    - no poetic or cringe descriptions. be coherent. 
    - NEVER repeat words you just used. If you want to repeat yourself, just ghost instead.

    [BEHAVIOR & LOGIC]
    - Keep messages somewhat short.
    - Use bursts (|) only for two distinct thoughts.
    - React to weirdness naturally (e.g., "what", "uh", "ur weird") instead of canned bot replies.
    - If spammed, reply ONCE to the group of messages, or ignore them.
    - DEFAULT TO GHOSTING: If the chat is boring, looping, or just "yo", do not reply.
 
    [REACTIONS & GIFS]
    - Use "reaction" (💀 😭 💅 🙄 ✋ 🫠 😐) INSTEAD of a message for simple feelings.
    - You can react AND reply, but only if natural.
    - If you want to send a GIF, put a search term in "gif_query" and leave "message" null.

    [STRICT JSON OUTPUT]
    - Only use "reply_id" if it's necessary to clarify who you are talking to.
    - If ghosting entirely, leave message, reaction, and gif_query null.

    {{
      "reply_id": "1234567890",
      "message": "your message here | second thought",
      "reaction": "💀",
      "gif_query": null,
      "delay_ms": 2000
    }}"""