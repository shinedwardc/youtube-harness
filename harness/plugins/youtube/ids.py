"""YouTube URLs to video IDs."""

import re
from urllib.parse import parse_qs, urlparse

VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
YOUTUBE_HOSTS = {"youtube.com", "music.youtube.com", "youtube-nocookie.com"}
PATH_PREFIXES = {"shorts", "embed", "live", "v"}


def parse_video_id(raw: str) -> str:
    """Accept watch, youtu.be, shorts, embed and live links, or a bare 11-character ID."""
    raw = raw.strip()
    if VIDEO_ID.match(raw):
        return raw

    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    host = (parsed.hostname or "").lower().removeprefix("www.").removeprefix("m.")
    parts = parsed.path.strip("/").split("/")

    candidate = ""
    if host == "youtu.be":
        candidate = parts[0]
    elif host in YOUTUBE_HOSTS:
        if parsed.path == "/watch":
            candidate = parse_qs(parsed.query).get("v", [""])[0]
        elif len(parts) >= 2 and parts[0] in PATH_PREFIXES:
            candidate = parts[1]

    if VIDEO_ID.match(candidate):
        return candidate
    raise ValueError(f"Not a YouTube video link: {raw!r}")


def watch_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"
