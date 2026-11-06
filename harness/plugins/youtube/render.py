"""Summary data to a markdown note in the vault."""

import json
import logging
import re
from pathlib import Path
from string import Template

from .transcript import parse_time

log = logging.getLogger(__name__)

NOTES_FOLDER = "youtube"
SLUG_LENGTH = 60


def slugify(title: str) -> str:
    """Lowercase, hyphenated, and safe on every OS Obsidian syncs to. Keeps Hangul and other letters."""
    slug = re.sub(r"[^\w\s-]", "", title.lower())
    slug = re.sub(r"[\s_-]+", "-", slug).strip("-")
    return slug[:SLUG_LENGTH].rstrip("-") or "video"


def note_path(data: dict) -> Path:
    # The ID keeps two videos with the same title from sharing a file.
    return Path(NOTES_FOLDER) / f"{slugify(data['title'])}-{data['video_id']}.md"


def render_note(template: str, data: dict) -> str:
    def quoted(value) -> str:
        # A JSON string is a valid YAML scalar, so titles with ':' or '#' stay intact.
        return json.dumps(value, ensure_ascii=False)

    timestamps = []
    for stamp in data["timestamps"]:
        seconds = parse_time(stamp["time"])
        time = f"[{stamp['time']}]({data['url']}&t={seconds}s)" if seconds is not None else stamp["time"]
        timestamps.append(f"- {time} {stamp['label']}")

    return Template(template).substitute(
        title=quoted(data["title"]),
        channel=quoted(data["channel"]),
        url=data["url"],
        video_id=data["video_id"],
        language=data["language"],
        captions=data["captions"],
        summarized=data["summarized"],
        model=quoted(data["model"]),
        tags=quoted(data["tags"]),
        tldr=data["tldr"],
        key_points="\n".join(f"- {point}" for point in data["key_points"]) or "- (none)",
        timestamps="\n".join(timestamps) or "- (none)",
    )


def write_note(template: str, data: dict, vault_dir: Path) -> Path:
    """Write the note and return its vault-relative path. An existing note is never overwritten."""
    relative = note_path(data)
    path = vault_dir / relative
    if path.exists():
        # It may hold the user's own notes; the cache normally stops us getting here.
        log.warning("Keeping the existing note at %s", path)
        return relative

    path.parent.mkdir(parents=True, exist_ok=True)
    # Write then rename, so a sync never picks up half a note.
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(render_note(template, data), encoding="utf-8")
    temporary.replace(path)
    return relative
