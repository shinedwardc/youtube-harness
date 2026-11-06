"""Cache, queue and job outcomes, matching the MVP's "done when" checks."""

from datetime import timedelta

from harness.core.jobs import Worker, run, submit
from harness.core.plugin import Unprocessable
from harness.plugins.youtube import YouTubePlugin
from tests.conftest import FakeLLM

URL = "https://youtu.be/dQw4w9WgXcQ"


def run_submitted(store, plugin, vault, llms, raw=URL):
    submission = submit(store, plugin, raw)
    job = store.claim(submission.job.id)
    return run(job, store=store, plugin=plugin, llms=llms, vault_dir=vault)


def test_a_new_link_goes_through_to_a_note(store, plugin, vault):
    job = run_submitted(store, plugin, vault, [FakeLLM()])

    assert job.status == "done"
    assert (vault / job.note_path).exists()
    assert store.get_summary("youtube", "dQw4w9WgXcQ").data["model"] == "fake:model"


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
