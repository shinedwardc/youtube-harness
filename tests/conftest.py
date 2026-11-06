"""Fakes for the network edges: the LLM and yt-dlp. Nothing in the suite goes online."""

import json

import pytest

from harness.core.db import Store
from harness.core.llm import LLMUnavailable
from harness.plugins.youtube import YouTubePlugin
from harness.plugins.youtube.fetch import Video

SUMMARY_REPLY = json.dumps(
    {
        "tldr": "Raft elects a leader and replicates a log.",
        "key_points": ["A leader is elected by majority vote.", "The leader replicates log entries."],
        "timestamps": [{"time": "00:00", "label": "Intro"}, {"time": "01:00", "label": "Leader election"}],
        "tags": ["Distributed Systems", "consensus"],
    }
)


class FakeLLM:
    """Answers from a list of replies, or raises LLMUnavailable when `down`."""

    def __init__(self, replies=None, *, name="fake:model", max_input_tokens=100_000, down=False):
        self.replies = list(replies) if replies is not None else None
        self.name = name
        self.max_input_tokens = max_input_tokens
        self.down = down
        self.calls: list[tuple[str, str]] = []

    def complete(self, system: str, user: str) -> str:
        self.calls.append((system, user))
        if self.down:
            raise LLMUnavailable(f"{self.name}: 503 Service Unavailable")
        if self.replies is None:
            return SUMMARY_REPLY
        return self.replies.pop(0)


def make_video(video_id="dQw4w9WgXcQ", *, language="en", transcript=None, title="How Raft Works"):
    return Video(
        video_id=video_id,
        title=title,
        channel="Example Channel",
        url=f"https://www.youtube.com/watch?v={video_id}",
        duration=120,
        category="Education",
        language=language,
        captions="creator",
        transcript=transcript or "[00:00] Welcome to the video.\n\n[01:00] Raft elects a leader.",
    )


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "harness.db")


@pytest.fixture
def vault(tmp_path):
    return tmp_path / "vault"


@pytest.fixture
def fetched():
    """The video IDs the fake fetcher was asked for."""
    return []


@pytest.fixture
def plugin(fetched):
    def fetcher(video_id):
        fetched.append(video_id)
        return make_video(video_id)

    return YouTubePlugin(fetcher=fetcher)
