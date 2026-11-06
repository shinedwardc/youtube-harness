"""The shape every plugin shares: fetch the input, process it with the LLM, write the output."""

from pathlib import Path
from typing import Any, Protocol

from .llm import LLM


class Unprocessable(Exception):
    """The input can't be processed as-is. The job ends with `status` instead of `failed`."""

    def __init__(self, status: str, message: str):
        super().__init__(message)
        self.status = status


class Plugin(Protocol):
    # Stored with every job and summary, so it must never change once data exists.
    name: str

    def parse(self, raw: str) -> str:
        """Turn user input (a URL) into a stable item ID. Raises ValueError if it isn't one."""
        ...

    def fetch(self, item_id: str) -> Any:
        """Download everything the summary needs. May raise Unprocessable."""
        ...

    def summarize(self, source: Any, llm: LLM) -> dict:
        """Return JSON-serializable data that write() can render without `source`."""
        ...

    def write(self, data: dict, vault_dir: Path) -> Path:
        """Save the note and return its path relative to vault_dir."""
        ...

    def source_text(self, source: Any) -> str:
        """The full text behind the summary, stored for search and Q&A."""
        ...
