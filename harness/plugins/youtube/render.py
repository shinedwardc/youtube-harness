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
    # Remove punctuation such as : " / ? #; \w keeps letters in any script, digits and _.
    slug = re.sub(r"[^\w\s-]", "", title.lower())
    # Collapse runs of spaces, underscores and hyphens into one hyphen.
    slug = re.sub(r"[\s_-]+", "-", slug).strip("-")
    # A title made only of punctuation leaves nothing, so fall back to "video".
    return slug[:SLUG_LENGTH].rstrip("-") or "video"


def note_path(data: dict) -> Path:
    # One folder per month summarized ("2026-11"), so notes never have to move later.
    month = data["summarized"][:7]
    # The ID keeps two videos with the same title from sharing a file.
    return Path(NOTES_FOLDER) / month / f"{slugify(data['title'])}-{data['video_id']}.md"


def render_note(template: str, data: dict) -> str:
    def quoted(value) -> str:
        # A JSON string is a valid YAML scalar, so titles with ':' or '#' stay intact.
        return json.dumps(value, ensure_ascii=False)

    # Each timestamp links to that second of the video; a time that can't be parsed stays plain text.
    timestamps = []
    for stamp in data["timestamps"]:
        seconds = parse_time(stamp["time"])
        time = f"[{stamp['time']}]({data['url']}&t={seconds}s)" if seconds is not None else stamp["time"]
        timestamps.append(f"- {time} {stamp['label']}")

    # Fill each $placeholder in templates/note.md.
    # Frontmatter values are quoted; the markdown body is inserted as-is.
    return Template(template).substitute(
        title=quoted(data["title"]),
        channel=quoted(data["channel"]),
        # Summaries cached before categories were added have none.
        category=quoted(data.get("category", "")),
        url=data["url"],
        video_id=data["video_id"],
        language=data["language"],
        captions=data["captions"],
        summarized=data["summarized"],
        model=quoted(data["model"]),
        tags=quoted(data["tags"]),
        # Also in the frontmatter, because Obsidian Bases can only show properties as columns.
        tldr_property=quoted(data["tldr"]),
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

    # Create vault/youtube/ on the first run.
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write then rename, so a sync never picks up half a note.
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(render_note(template, data), encoding="utf-8")
    temporary.replace(path)
    # The relative path is what gets stored, so it still works if the vault moves.
    return relative
