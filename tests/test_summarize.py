"""One call when the transcript fits, map-reduce when it doesn't, and one re-ask on bad JSON."""

import json

import pytest

from harness.core.config import PROJECT_ROOT
from harness.plugins.youtube.summarize import (
    Summarizer,
    SummaryError,
    estimate_tokens,
    normalize_tag,
    parse_summary,
    split_chunks,
)
from tests.conftest import SUMMARY_REPLY, FakeLLM, make_video


@pytest.fixture
def summarizer():
    return Summarizer(
        summary_prompt=(PROJECT_ROOT / "prompts" / "summary.md").read_text(),
        chunk_prompt=(PROJECT_ROOT / "prompts" / "chunk.md").read_text(),
    )


def long_transcript(minutes):
    return "\n\n".join(f"[{m:02d}:00] " + "word " * 200 for m in range(minutes))


def test_short_transcript_is_one_call(summarizer):
    llm = FakeLLM()
    summary = summarizer.summarize(make_video(), llm)

    assert len(llm.calls) == 1
    assert summary.tldr.startswith("Raft")
    assert "Transcript:" in llm.calls[0][1]


def test_long_transcript_is_map_reduced(summarizer):
    llm = FakeLLM(["- [00:00] part one", "- [05:00] part two", SUMMARY_REPLY], max_input_tokens=1_500)
    summarizer.summarize(make_video(transcript=long_transcript(10)), llm)

    assert len(llm.calls) == 3
    assert "part 1 of 2" in llm.calls[0][0]
    final_user = llm.calls[-1][1]
    assert "Notes from consecutive parts" in final_user
    assert "part one" in final_user and "part two" in final_user


def test_auto_language_follows_the_captions(summarizer):
    llm = FakeLLM()
    summarizer.summarize(make_video(language="ko"), llm)
    assert "in Korean" in llm.calls[0][0]


def test_configured_language_overrides_the_captions(summarizer):
    summarizer.summary_language = "en"
    llm = FakeLLM()
    summarizer.summarize(make_video(language="ko"), llm)
    assert "in English" in llm.calls[0][0]


def test_bad_json_is_asked_for_once_more(summarizer):
    llm = FakeLLM(["Sure! Here is a summary of the video.", SUMMARY_REPLY])
    summary = summarizer.summarize(make_video(), llm)
    assert len(llm.calls) == 2
    assert "not valid JSON" in llm.calls[1][1]
    assert summary.key_points


def test_bad_json_twice_raises(summarizer):
    with pytest.raises(SummaryError):
        summarizer.summarize(make_video(), FakeLLM(["nope", '{"tldr": "missing fields"}']))


def test_tags_are_normalized_for_obsidian(summarizer):
    summary = summarizer.summarize(make_video(), FakeLLM())
    assert summary.tags == ["distributed-systems", "consensus"]
    assert normalize_tag("#Machine Learning!") == "machine-learning"


def test_highlights_are_cleaned_and_capped(summarizer):
    reply = json.loads(SUMMARY_REPLY) | {"highlights": ["- Leader election.", " ", "• Log replication", "Safety", "Extras"]}
    summary = summarizer.summarize(make_video(), FakeLLM([json.dumps(reply)]))
    assert summary.highlights == ["Leader election", "Log replication", "Safety"]


def test_a_summary_without_highlights_is_still_kept(summarizer):
    reply = json.loads(SUMMARY_REPLY)
    del reply["highlights"]
    llm = FakeLLM([json.dumps(reply)])
    assert summarizer.summarize(make_video(), llm).highlights == []
    assert len(llm.calls) == 1


def test_parse_summary_tolerates_fences_and_prose():
    assert parse_summary(f"Here you go:\n```json\n{SUMMARY_REPLY}\n```").tldr


def test_token_estimate_counts_hangul_per_character():
    assert estimate_tokens("abcd" * 10) == 10
    assert estimate_tokens("안녕하세요") == 5


def test_chunks_stay_under_budget_and_keep_paragraphs_whole():
    text = long_transcript(10)
    chunks = split_chunks(text, 600)
    assert all(estimate_tokens(chunk) <= 600 for chunk in chunks)
    assert "\n\n".join(chunks) == text
