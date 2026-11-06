"""Notes: valid frontmatter, clickable timestamps, safe filenames, and never a clobbered note."""

import json

from harness.core.config import PROJECT_ROOT
from harness.plugins.youtube.render import render_note, slugify, write_note

TEMPLATE = (PROJECT_ROOT / "templates" / "note.md").read_text()


def data(**overrides):
    return {
        "video_id": "dQw4w9WgXcQ",
        "title": 'Raft: "Consensus" #1',
        "channel": "Example Channel",
        "category": "Science & Technology",
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "language": "en",
        "captions": "auto",
        "summarized": "2026-11-10",
        "model": "gemini:gemini-3.5-flash-lite",
        "tldr": "One or two sentences.",
        "key_points": ["First point."],
        "timestamps": [{"time": "03:10", "label": "Leader election"}, {"time": "around the end", "label": "Outro"}],
        "tags": ["distributed-systems", "consensus"],
        **overrides,
    }


def frontmatter(note: str) -> dict:
    """Every value is JSON or a bare token, so this reads it without a YAML dependency."""
    block = note.split("---\n")[1]
    fields = {}
    for line in block.strip().splitlines():
        key, value = line.split(": ", 1)
        try:
            fields[key] = json.loads(value)
        except json.JSONDecodeError:
            fields[key] = value
    return fields


def test_frontmatter_survives_quotes_colons_and_hashes():
    fields = frontmatter(render_note(TEMPLATE, data()))
    assert fields["title"] == 'Raft: "Consensus" #1'
    assert fields["tags"] == ["distributed-systems", "consensus"]
    assert fields["summarized"] == "2026-11-10"
    assert fields["category"] == "Science & Technology"
    # Duplicated from the body so Obsidian Bases can show it as a column.
    assert fields["tldr"] == "One or two sentences."


def test_summaries_cached_before_categories_still_render():
    old = data()
    del old["category"]
    assert frontmatter(render_note(TEMPLATE, old))["category"] == ""


def test_timestamps_link_to_that_moment():
    note = render_note(TEMPLATE, data())
    assert "- [03:10](https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=190s) Leader election" in note
    # A time the model made up in prose is shown but not linked.
    assert "- around the end Outro" in note


def test_note_keeps_the_sections_from_the_design_doc():
    note = render_note(TEMPLATE, data())
    for heading in ("## TL;DR", "## Key points", "## Timestamps", "## My notes"):
        assert heading in note


def test_slug_is_filesystem_safe_and_keeps_hangul():
    assert slugify('Raft: "Consensus" / Part #1?') == "raft-consensus-part-1"
    assert slugify("래프트 합의 알고리즘") == "래프트-합의-알고리즘"
    assert slugify("???") == "video"


def test_writes_into_a_folder_for_the_month_summarized(tmp_path):
    relative = write_note(TEMPLATE, data(), tmp_path)
    assert str(relative) == "youtube/2026-11/raft-consensus-1-dQw4w9WgXcQ.md"
    assert (tmp_path / relative).read_text().startswith("---\ntitle:")
    assert not list((tmp_path / "youtube" / "2026-11").glob(".*.tmp"))


def test_a_new_month_gets_a_new_folder(tmp_path):
    assert str(write_note(TEMPLATE, data(summarized="2026-12-01"), tmp_path)).startswith("youtube/2026-12/")


def test_never_overwrites_an_existing_note(tmp_path):
    relative = write_note(TEMPLATE, data(), tmp_path)
    (tmp_path / relative).write_text("my own notes")
    write_note(TEMPLATE, data(tldr="different"), tmp_path)
    assert (tmp_path / relative).read_text() == "my own notes"
