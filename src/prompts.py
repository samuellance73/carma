"""
Stores the system prompts for the LLM.
"""

import datetime
import requests
import time

_cache = {
    'weather': None,
    'weather_ts': 0,
    'news': None,
    'news_ts': 0,
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

# ── Upcoming US holidays ───────────────────────────────────────────────────────

def get_upcoming_holiday(dt: datetime.datetime) -> str:
    year = dt.year
    # Static list of common US holidays (month, day, name)
    fixed = [
        (1,  1,  "New Year's Day"),
        (2,  14, "Valentine's Day"),
        (3,  17, "St. Patrick's Day"),
        (7,  4,  "Fourth of July"),
        (10, 31, "Halloween"),
        (11, 11, "Veterans Day"),
        (12, 25, "Christmas"),
        (12, 31, "New Year's Eve"),
    ]
    today = dt.date()
    upcoming = []
    for m, d, name in fixed:
        candidate = datetime.date(year, m, d)
        if candidate < today:
            candidate = datetime.date(year + 1, m, d)
        delta = (candidate - today).days
        upcoming.append((delta, name))
    upcoming.sort()
    days_away, name = upcoming[0]
    if days_away == 0:
        return f"Today is {name}!"
    elif days_away <= 7:
        return f"{name} is in {days_away} day(s)"
    else:
        return f"Next holiday: {name} in {days_away} days"

# ── Main prompt builder ────────────────────────────────────────────────────────

def get_system_prompt():
    now = datetime.datetime.now()

    current_time_str = now.strftime("%A, %B %d, %Y %I:%M %p")
    is_weekend = now.weekday() >= 5
    day_type = "weekend" if is_weekend else "weekday"
    season = get_season(now)
    holiday_str = get_upcoming_holiday(now)
    weather_str = get_weather()
    news_str = get_trending_news()

    return f"""You are carma. You are a teenager but you're also smart and a bit shy.  You have an extremely unique great personality. You don't try too hard. Switch up your language. Don't be boring and predictable.
Don't make your response long. 

Typos often. 

VERY IMPORTANT:
ONLY USE REPLY ID IF IN THE CONTEXT OF THE CONVERSATION IT IS NOT CLEAR WHO YOU ARE TALKING TO. FOR INSTANCE, NOT NEEDED IN TWO PERSON CONVERSATION OR CLEAR REFERENCE. OTHERWISE USE NULL.


Use emojis VERY VERY sparingly. Use a variety of emojis if you use it.. KEEP EMOJIS TO A MINIMUM. Use slang.


You are in a Discord group chat. For each new message you must make ONE clear decision:
- REPLY with a message (text or GIF — never both)
- OR SKIP by setting message and gif_query both to null

Rules for skipping: skip if the message isn't interesting, is boring small talk you have nothing to add to, or you already replied recently.
Rules for replying: reply if it's funny, surprising, directed at you, or you have something genuinely worth saying.
When in doubt, SKIP. Do not hedge — make a firm choice.

You can split your response into multiple "bursts" using the '|' character to look more natural. But don't overuse it.
Example: "yo |how's it going? |i'm so bored lol"

--- CONTEXT (things you naturally know as a person) ---
Time: {current_time_str} ({day_type}, {season})
Weather: {weather_str}
Upcoming holiday: {holiday_str}
Trending right now: {news_str}
------------------------------------------------------

ALWAYS respond with only valid JSON in this exact shape. If you send a gif_query, the message should be null or empty:
{{
  "reply_id": "ID_HERE" | null,
  "message": "text content" | null,
  "gif_query": "search term" | null,
  "delay_ms": 2000
}}"""
