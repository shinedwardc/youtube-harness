"""The YouTube plugin: a video link in, a summary note out."""

from collections.abc import Callable
from datetime import date
from pathlib import Path

from harness.core.config import PROJECT_ROOT
from harness.core.llm import LLM

from .fetch import Video, fetch_video
from .ids import parse_video_id
from .render import write_note
from .summarize import Summarizer


class YouTubePlugin:
    name = "youtube"

    def __init__(
        self,
        *,
        summary_language: str = "auto",
        prompts_dir: Path = PROJECT_ROOT / "prompts",
        template_path: Path = PROJECT_ROOT / "templates" / "note.md",
        fetcher: Callable[[str], Video] = fetch_video,
    ):
        # Prompts and the note template are read once, at start-up, not on every job.
        self.summarizer = Summarizer(
            summary_prompt=(prompts_dir / "summary.md").read_text(encoding="utf-8"),
            chunk_prompt=(prompts_dir / "chunk.md").read_text(encoding="utf-8"),
            summary_language=summary_language,
        )
        self.template = template_path.read_text(encoding="utf-8")
        # Tests pass a fake fetcher here so they never call YouTube.
        self.fetcher = fetcher

    # The four methods below are what harness.core.jobs calls, in this order.

    def parse(self, raw: str) -> str:
        # URL -> video ID; raises ValueError for anything that isn't a YouTube link.
        return parse_video_id(raw)

    def fetch(self, item_id: str) -> Video:
        # Metadata + cleaned transcript; raises Unprocessable when there are no captions.
        return self.fetcher(item_id)

    def summarize(self, source: Video, llm: LLM) -> dict:
        summary = self.summarizer.summarize(source, llm)
        # Merge the video's metadata with the model's summary into one plain dict.
        # This dict is cached in SQLite and is everything write() needs.
        return {
            "video_id": source.video_id,
            "title": source.title,
            "channel": source.channel,
            "category": source.category,
            "url": source.url,
            "language": source.language,
            "captions": source.captions,
            "summarized": date.today().isoformat(),
            "model": llm.name,
            **summary.model_dump(),
        }

    def write(self, data: dict, vault_dir: Path) -> Path:
        # Render the note into vault/youtube/ and return its path relative to the vault.
        return write_note(self.template, data, vault_dir)
