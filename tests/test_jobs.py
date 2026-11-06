"""Cache, queue and job outcomes, matching the MVP's "done when" checks."""

import threading
from datetime import timedelta

import pytest

from harness.core.jobs import Worker, backfill_source_texts, run, submit, wait
from harness.core.plugin import Unprocessable
from harness.plugins.youtube import YouTubePlugin
from tests.conftest import FakeLLM, abandon, make_video

URL = "https://youtu.be/dQw4w9WgXcQ"


def run_submitted(store, plugin, vault, llms, raw=URL):
    submission = submit(store, plugin, raw)
    job = store.claim(submission.job.id)
    return run(job, store=store, plugin=plugin, llms=llms, vault_dir=vault)


def test_a_new_link_goes_through_to_a_note(store, plugin, vault):
    job = run_submitted(store, plugin, vault, [FakeLLM()])

    assert job.status == "done"
    assert (vault / job.note_path).exists()
    data = store.get_summary("youtube", "dQw4w9WgXcQ").data
    assert data["model"] == "fake:model"
    assert data["category"] == "Education"


def test_a_finished_job_keeps_the_whole_transcript_apart_from_the_summary(store, vault):
    transcript = "\n\n".join(f"[{minute:02d}:00] Words spoken in minute {minute}." for minute in range(600))
    plugin = YouTubePlugin(fetcher=lambda video_id: make_video(video_id, transcript=transcript))

    run_submitted(store, plugin, vault, [FakeLLM()])

    assert store.get_source_text("youtube", "dQw4w9WgXcQ") == transcript
    # GET /jobs reads every summary on each poll, so the transcript must stay out of them.
    assert transcript not in str(store.get_summary("youtube", "dQw4w9WgXcQ").data)


def seed_summary_without_transcript(store, video_id):
    """A video summarized before transcripts were kept."""
    job = store.claim(store.create_job("youtube", video_id, video_id).id)
    store.finish(job, f"youtube/{video_id}.md", {"title": video_id})


def test_backfill_fetches_only_what_is_missing_without_calling_an_llm(store, plugin, vault, fetched):
    run_submitted(store, plugin, vault, [FakeLLM()])
    fetched.clear()
    seed_summary_without_transcript(store, "aaaaaaaaaaa")

    assert backfill_source_texts(store, {"youtube": plugin}) == (1, 0)

    assert fetched == ["aaaaaaaaaaa"]
    assert store.get_source_text("youtube", "aaaaaaaaaaa") == make_video().transcript
    assert store.summaries_without_source_text() == []


def test_backfill_survives_a_failure_and_a_second_run_retries_it(store, plugin):
    seed_summary_without_transcript(store, "aaaaaaaaaaa")
    seed_summary_without_transcript(store, "bbbbbbbbbbb")

    def fetcher(video_id):
        if video_id == "aaaaaaaaaaa":
            raise Unprocessable("failed", "Video unavailable")
        return make_video(video_id)

    assert backfill_source_texts(store, {"youtube": YouTubePlugin(fetcher=fetcher)}) == (1, 1)
    assert store.summaries_without_source_text() == [("youtube", "aaaaaaaaaaa")]

    assert backfill_source_texts(store, {"youtube": plugin}) == (1, 0)
    assert store.summaries_without_source_text() == []


def test_the_same_link_twice_comes_from_the_cache(store, plugin, vault, fetched):
    llm = FakeLLM()
    first = run_submitted(store, plugin, vault, [llm])

    again = submit(store, plugin, "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=5s")

    assert again.job is None
    assert again.summary.note_path == first.note_path
    assert fetched == ["dQw4w9WgXcQ"]
    assert len(llm.calls) == 1


def test_a_link_sent_while_queued_joins_the_existing_job(store, plugin):
    first = submit(store, plugin, URL)
    second = submit(store, plugin, "dQw4w9WgXcQ")
    assert second.job.id == first.job.id


def test_a_job_can_only_be_claimed_once(store, plugin):
    job = submit(store, plugin, URL).job
    assert store.claim(job.id) is not None
    assert store.claim(job.id) is None
    assert store.claim() is None


def test_no_captions_ends_as_needs_transcription(store, vault):
    def fetcher(video_id):
        raise Unprocessable("needs_transcription", "The video has no creator captions or auto-captions")

    job = run_submitted(store, YouTubePlugin(fetcher=fetcher), vault, [FakeLLM()])

    assert job.status == "needs_transcription"
    assert "no creator captions" in job.error
    # Not cached, so it can be retried once Phase 3 can transcribe it.
    assert store.get_summary("youtube", "dQw4w9WgXcQ") is None


def test_an_unexpected_error_fails_the_job_without_raising(store, vault):
    def fetcher(video_id):
        raise RuntimeError("yt-dlp exploded")

    job = run_submitted(store, YouTubePlugin(fetcher=fetcher), vault, [FakeLLM()])

    assert job.status == "failed"
    assert job.error == "RuntimeError: yt-dlp exploded"


def test_falls_back_to_the_next_provider(store, plugin, vault):
    primary, fallback = FakeLLM(name="gemini:x", down=True), FakeLLM(name="groq:y")
    job = run_submitted(store, plugin, vault, [primary, fallback])

    assert job.status == "done"
    assert store.get_summary("youtube", "dQw4w9WgXcQ").data["model"] == "groq:y"


def test_every_provider_down_fails_the_job(store, plugin, vault):
    job = run_submitted(store, plugin, vault, [FakeLLM(down=True), FakeLLM(name="groq:y", down=True)])
    assert job.status == "failed"
    assert "No provider could answer" in job.error


def test_a_failed_job_can_be_sent_again(store, vault, plugin):
    broken = YouTubePlugin(fetcher=lambda video_id: (_ for _ in ()).throw(RuntimeError("down")))
    failed = run_submitted(store, broken, vault, [FakeLLM()])

    retried = run_submitted(store, plugin, vault, [FakeLLM()])

    assert failed.status == "failed"
    assert retried.id != failed.id and retried.status == "done"


def test_worker_runs_queued_jobs_in_order(store, plugin, vault, fetched):
    submit(store, plugin, "https://youtu.be/aaaaaaaaaaa")
    submit(store, plugin, "https://youtu.be/bbbbbbbbbbb")
    worker = Worker(store=store, plugins={"youtube": plugin}, llms=[FakeLLM()], vault_dir=vault)

    assert worker.run_once().status == "done"
    assert worker.run_once().status == "done"
    assert worker.run_once() is None
    assert fetched == ["aaaaaaaaaaa", "bbbbbbbbbbb"]


def test_stale_jobs_are_requeued(store, plugin):
    job = submit(store, plugin, URL).job
    store.claim(job.id)

    assert store.requeue_stale(timedelta(minutes=30)) == 0
    assert store.requeue_stale(timedelta(seconds=-1)) == 1
    assert store.get_job(job.id).status == "queued"


def test_running_worker_recovers_an_abandoned_job_without_a_restart(store, plugin, vault):
    worker = Worker(store=store, plugins={"youtube": plugin}, llms=[FakeLLM()], vault_dir=vault)
    job = submit(store, plugin, URL).job
    store.claim(job.id)
    abandon(store, job.id)

    finished = worker.run_once()

    assert finished.id == job.id and finished.status == "done"


def test_worker_leaves_a_recently_updated_job_alone(store, plugin, vault):
    worker = Worker(store=store, plugins={"youtube": plugin}, llms=[FakeLLM()], vault_dir=vault)
    job = submit(store, plugin, URL).job
    store.claim(job.id)

    assert worker.run_once() is None
    assert store.get_job(job.id).status == "fetching"


def test_wait_returns_an_abandoned_job_to_the_queue(store, plugin):
    job = submit(store, plugin, URL).job
    store.claim(job.id)
    abandon(store, job.id)

    assert wait(store, job.id, poll_interval=0.01).status == "queued"


def test_wait_returns_a_finished_job(store, plugin, vault):
    job = run_submitted(store, plugin, vault, [FakeLLM()])

    assert wait(store, job.id, poll_interval=0.01).status == "done"


def test_an_interrupted_job_is_closed_and_can_be_sent_again(store, plugin, vault):
    def fetcher(video_id):
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        run_submitted(store, YouTubePlugin(fetcher=fetcher), vault, [FakeLLM()])

    interrupted = store.get_job(1)
    assert interrupted.status == "failed"
    assert interrupted.error == "Interrupted before finishing"

    retried = run_submitted(store, plugin, vault, [FakeLLM()])
    assert retried.id != interrupted.id and retried.status == "done"


def test_shutdown_requeues_the_job_still_running(store, vault):
    started, release = threading.Event(), threading.Event()

    def fetcher(video_id):
        started.set()
        release.wait(5)
        raise RuntimeError("released by the test")

    plugin = YouTubePlugin(fetcher=fetcher)
    job = submit(store, plugin, URL).job
    worker = Worker(store=store, plugins={"youtube": plugin}, llms=[FakeLLM()], vault_dir=vault, poll_interval=0.01)
    worker.start()
    assert started.wait(5)

    worker.stop(timeout=0.01)
    status_after_stop = store.get_job(job.id).status

    release.set()
    worker._thread.join(5)
    assert status_after_stop == "queued"


def test_shutdown_leaves_a_finished_job_alone(store, plugin, vault):
    job = run_submitted(store, plugin, vault, [FakeLLM()])
    worker = Worker(store=store, plugins={"youtube": plugin}, llms=[FakeLLM()], vault_dir=vault, poll_interval=0.01)
    worker.start()

    worker.stop()

    assert store.get_job(job.id).status == "done"
