"""Video metadata and captions via yt-dlp, without downloading the video."""

import logging
from dataclasses import dataclass

from yt_dlp import YoutubeDL
from yt_dlp.networking.exceptions import RequestError
from yt_dlp.utils import DownloadError

from harness.core.plugin import Unprocessable
from harness.core.retry import retry

from .ids import watch_url
from .transcript import clean_vtt

log = logging.getLogger(__name__)

YDL_OPTIONS = {
    "skip_download": True,
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "logger": logging.getLogger("yt_dlp"),
}


@dataclass(frozen=True)
class Track:
    language: str
    kind: str  # "creator" or "auto"
    url: str


@dataclass(frozen=True)
class Video:
    video_id: str
    title: str
    channel: str
    url: str
    duration: int | None
    category: str  # YouTube's own, e.g. "Education"; "" when missing
    language: str
    captions: str  # "creator" or "auto"
    transcript: str


def fetch_video(video_id: str, *, retry_options: dict | None = None) -> Video:
    url = watch_url(video_id)
    retry_options = retry_options or {}
    with YoutubeDL(YDL_OPTIONS) as ydl:
        # Step 1: read the video's page data (title, channel, caption tracks). No video download.
        # yt-dlp wraps network and "unavailable" errors alike, so both get retried.
        info = retry(
            lambda: ydl.extract_info(url, download=False),
            what=f"yt-dlp metadata for {video_id}",
            retry_on=(DownloadError,),
            **retry_options,
        )
        # A stream that hasn't finished has no complete captions yet.
        if info.get("live_status") in ("is_live", "is_upcoming"):
            raise Unprocessable("failed", "Live or upcoming stream; send it again once it has ended")

        # Step 2: pick one caption track. No track at all means Phase 3's transcription is needed.
        track = choose_track(info)
        if track is None:
            raise Unprocessable("needs_transcription", "The video has no creator captions or auto-captions")

        # Step 3: download that track's .vtt file. ydl.urlopen sends the same headers yt-dlp uses.
        log.info("Using %s captions (%s)", track.kind, track.language)
        vtt = retry(
            lambda: ydl.urlopen(track.url).read().decode("utf-8"),
            what=f"caption download for {video_id}",
            retry_on=(RequestError, OSError),
            **retry_options,
        )

    # Step 4: turn the VTT into plain text with [mm:ss] markers.
    transcript = clean_vtt(vtt)
    if not transcript:
        raise Unprocessable("needs_transcription", "The caption file is empty")

    # Keep only the fields later steps need; the rest of `info` is dropped.
    return Video(
        video_id=video_id,
        title=info.get("title") or video_id,
        channel=info.get("channel") or info.get("uploader") or "",
        url=url,
        duration=info.get("duration"),
        # The creator picks one of about 15 fixed categories; yt-dlp returns it as a list.
        category=(info.get("categories") or [""])[0],
        language=track.language,
        captions=track.kind,
        transcript=transcript,
    )


def choose_track(info: dict) -> Track | None:
    """Creator captions first, in the video's language when known; then the original auto-captions."""
    # yt-dlp reports codes like "en-US"; base is just "en".
    language = (info.get("language") or "").lower()
    base = language.split("-")[0]

    # Creator captions, uploaded by the channel. "live_chat" is a chat replay, not captions.
    creator = {key: formats for key, formats in (info.get("subtitles") or {}).items() if key != "live_chat"}
    # Preference order: exact language, same base language, English, then anything.
    # Duplicates are harmless; the first key with a VTT file wins.
    wanted = [key for key in creator if key.lower() == language]
    wanted += [key for key in creator if base and key.lower().split("-")[0] == base]
    wanted += [key for key in creator if key.lower().split("-")[0] == "en"]
    wanted += list(creator)
    for key in wanted:
        if url := _vtt_url(creator[key]):
            return Track(language=_base_language(key), kind="creator", url=url)

    # Auto-captions list a machine translation for every language. "-orig" marks the
    # track made from the audio, so only that one (or the video's own language) is used.
    auto = info.get("automatic_captions") or {}
    wanted = [f"{base}-orig", base] if base else []
    # Language unknown: any "-orig" track is still the original audio.
    wanted += [key for key in auto if key.endswith("-orig")]
    for key in wanted:
        if key in auto and (url := _vtt_url(auto[key])):
            return Track(language=_base_language(key), kind="auto", url=url)
    return None


def _vtt_url(formats: list[dict]) -> str | None:
    # Each track is offered in several formats (json3, srv3, vtt...); only VTT is parsed.
    return next((f["url"] for f in formats if f.get("ext") == "vtt" and f.get("url")), None)


def _base_language(key: str) -> str:
    # "ko-orig" -> "ko", "en-US" -> "en".
    return key.removesuffix("-orig").split("-")[0].lower()
