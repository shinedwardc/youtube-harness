"""Transcript to structured summary: one call when it fits, map-reduce when it doesn't."""

import logging
import re
from string import Template

from pydantic import BaseModel, ValidationError

from harness.core.llm import LLM

from .fetch import Video

log = logging.getLogger(__name__)

LANGUAGE_NAMES = {
    "en": "English",
    "ko": "Korean",
    "ja": "Japanese",
    "zh": "Chinese",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
}


class Timestamp(BaseModel):
    time: str
    label: str


class Summary(BaseModel):
    tldr: str
    key_points: list[str]
    timestamps: list[Timestamp]
    tags: list[str]


class SummaryError(Exception):
    """The model's reply could not be parsed, even after asking again."""


def estimate_tokens(text: str) -> int:
    """About 4 characters per token for ASCII; count every other character (Hangul, kanji) as one."""
    ascii_chars = sum(1 for char in text if char.isascii())
    return ascii_chars // 4 + (len(text) - ascii_chars)


def split_chunks(text: str, max_tokens: int) -> list[str]:
    """Pack whole paragraphs (one per minute marker) into chunks under max_tokens."""
    chunks: list[str] = []
    current: list[str] = []
    size = 0
    for paragraph in text.split("\n\n"):
        tokens = estimate_tokens(paragraph)
        if current and size + tokens > max_tokens:
            chunks.append("\n\n".join(current))
            current, size = [], 0
        current.append(paragraph)
        size += tokens
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def language_name(code: str) -> str:
    return LANGUAGE_NAMES.get(code, code)


def parse_summary(reply: str) -> Summary:
    """Take the outermost {...} so stray prose or ``` fences around the JSON don't matter."""
    start, end = reply.find("{"), reply.rfind("}")
    if start == -1 or end < start:
        raise ValueError("no JSON object in the reply")
    return Summary.model_validate_json(reply[start : end + 1])


def normalize_tag(tag: str) -> str:
    """Obsidian tags can't contain spaces or most punctuation."""
    tag = re.sub(r"[^\w/-]+", "-", tag.strip().lstrip("#").lower())
    return re.sub(r"-{2,}", "-", tag).strip("-")


class Summarizer:
    def __init__(self, summary_prompt: str, chunk_prompt: str, summary_language: str = "auto"):
        self.summary_prompt = Template(summary_prompt)
        self.chunk_prompt = Template(chunk_prompt)
        self.summary_language = summary_language

    def summarize(self, video: Video, llm: LLM) -> Summary:
        code = video.language if self.summary_language == "auto" else self.summary_language
        language = language_name(code)
        header = f"Title: {video.title}\nChannel: {video.channel}\n\n"

        text, kind = video.transcript, "Transcript"
        while estimate_tokens(text) > llm.max_input_tokens:
            chunks = split_chunks(text, llm.max_input_tokens)
            if len(chunks) == 1:
                # One paragraph is over the budget; send it rather than loop forever.
                break
            log.info("Map-reduce: %d chunks for %s", len(chunks), llm.name)
            notes = [
                llm.complete(
                    self.chunk_prompt.substitute(language=language, part=f"part {i} of {len(chunks)}"),
                    header + chunk,
                )
                for i, chunk in enumerate(chunks, start=1)
            ]
            text, kind = "\n\n".join(notes), "Notes from consecutive parts of the transcript"

        system = self.summary_prompt.substitute(language=language)
        user = f"{header}{kind}:\n\n{text}"
        reply = llm.complete(system, user)
        try:
            summary = parse_summary(reply)
        except (ValueError, ValidationError) as error:
            log.warning("Unparseable summary from %s (%s); asking once more", llm.name, error)
            retry_note = "\n\nYour previous reply was not valid JSON in the required shape. Reply with only the JSON object."
            reply = llm.complete(system, user + retry_note)
            try:
                summary = parse_summary(reply)
            except (ValueError, ValidationError) as error:
                raise SummaryError(f"{llm.name} did not return valid summary JSON: {error}") from error

        summary.tags = [tag for tag in dict.fromkeys(map(normalize_tag, summary.tags)) if tag]
        return summary
