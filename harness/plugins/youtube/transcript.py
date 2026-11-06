"""WebVTT captions to plain text with a timestamp marker about once a minute."""

import html
import re
from collections import deque

TAG = re.compile(r"<[^>]+>")
MARKER_EVERY_SECONDS = 60


def parse_vtt(vtt: str) -> list[tuple[float, str]]:
    """Return (start seconds, line) pairs with tags stripped and rolling repeats removed."""
    segments: list[tuple[float, str]] = []
    # Auto-captions repeat the previous line at the top of each cue, sometimes twice.
    recent: deque[str] = deque(maxlen=3)

    # Only a truly empty line ends a cue: auto-captions put a lone space right after the timing.
    for block in re.split(r"\n{2,}", vtt.replace("\r\n", "\n")):
        lines = block.strip().split("\n")
        timing = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if timing is None:
            # The WEBVTT header, NOTE and STYLE blocks.
            continue
        start = _seconds(lines[timing].split("-->")[0])
        for line in lines[timing + 1 :]:
            text = " ".join(html.unescape(TAG.sub("", line)).split())
            if not text or text in recent:
                continue
            recent.append(text)
            segments.append((start, text))
    return segments


def to_text(segments: list[tuple[float, str]], every: float = MARKER_EVERY_SECONDS) -> str:
    """Join lines into paragraphs, each starting with a [mm:ss] marker."""
    paragraphs = []
    marker: float | None = None
    current: list[str] = []
    for start, line in segments:
        if marker is None or start - marker >= every:
            if current:
                paragraphs.append(f"[{format_time(marker)}] {' '.join(current)}")
            marker, current = start, []
        current.append(line)
    if current:
        paragraphs.append(f"[{format_time(marker)}] {' '.join(current)}")
    return "\n\n".join(paragraphs)


def clean_vtt(vtt: str) -> str:
    return to_text(parse_vtt(vtt))


def format_time(seconds: float) -> str:
    total = int(seconds)
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"


def parse_time(text: str) -> int | None:
    """'03:10' or '1:02:03' to seconds; None for anything else."""
    parts = text.strip().split(":")
    if not 2 <= len(parts) <= 3 or not all(part.isdigit() for part in parts):
        return None
    seconds = 0
    for part in parts:
        seconds = seconds * 60 + int(part)
    return seconds


def _seconds(timestamp: str) -> float:
    """'00:01:02.500' or '01:02.500' to seconds."""
    value = 0.0
    for part in timestamp.strip().replace(",", ".").split(":"):
        value = value * 60 + float(part)
    return value
