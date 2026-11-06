"""Submitting, running and polling jobs. Phase 2 replaces Worker with the custom scheduler."""

import logging
import threading
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from .db import Job, Store, Summary
from .llm import LLM, LLMUnavailable
from .plugin import Plugin, Unprocessable

log = logging.getLogger(__name__)

# A job not updated for this long belonged to a process that died.
STALE_AFTER = timedelta(minutes=30)


@dataclass(frozen=True)
class Submission:
    item_id: str
    job: Job | None = None
    summary: Summary | None = None


def submit(store: Store, plugin: Plugin, raw: str) -> Submission:
    """Return the cached summary, or queue a job. Raises ValueError for input the plugin rejects."""
    item_id = plugin.parse(raw)
    summary = store.get_summary(plugin.name, item_id)
    if summary is not None:
        return Submission(item_id, summary=summary)
    return Submission(item_id, job=store.create_job(plugin.name, item_id, raw))


def run(job: Job, *, store: Store, plugin: Plugin, llms: Sequence[LLM], vault_dir: Path) -> Job:
    """Take a claimed job through fetch, summarize and write.

    The outcome is in the job. Only an interrupt (Ctrl+C) raises, once the job is closed.
    """
    try:
        cached = store.get_summary(plugin.name, job.item_id)
        if cached is not None:
            # Another job finished this item after ours was queued.
            store.finish(job, cached.note_path)
            return store.get_job(job.id)

        log.info("Fetching %s %s", plugin.name, job.item_id)
        source = plugin.fetch(job.item_id)

        store.set_status(job.id, "summarizing")
        data = _summarize(plugin, source, llms, store, job.id)

        store.set_status(job.id, "writing")
        note_path = plugin.write(data, vault_dir)
        store.finish(job, str(note_path), data, source_text=plugin.source_text(source))
        log.info("Wrote %s", note_path)
    # `outcome` marks how the job ended, so a caller that reports that itself (the CLI) can skip these.
    except Unprocessable as error:
        log.warning("%s %s: %s", plugin.name, job.item_id, error, extra={"outcome": True})
        store.set_status(job.id, error.status, error=str(error))
    except Exception as error:
        log.exception("Job %d failed", job.id, extra={"outcome": True})
        store.set_status(job.id, "failed", error=f"{type(error).__name__}: {error}")
    except (KeyboardInterrupt, SystemExit):
        # Not `Exception`s, but the job won't finish; left open it would look busy and block a resend.
        store.set_status(job.id, "failed", error="Interrupted before finishing")
        raise
    return store.get_job(job.id)


class _Heartbeat:
    """An LLM that marks its job alive after each reply, as a long map-reduce can outlast STALE_AFTER."""

    def __init__(self, llm: LLM, store: Store, job_id: int):
        self.llm = llm
        self.store = store
        self.job_id = job_id
        self.name = llm.name
        self.max_input_tokens = llm.max_input_tokens

    def complete(self, system: str, user: str) -> str:
        reply = self.llm.complete(system, user)
        self.store.touch(self.job_id)
        return reply


def _summarize(plugin: Plugin, source, llms: Sequence[LLM], store: Store, job_id: int) -> dict:
    """Try each provider in order. Only an unavailable provider moves on to the next."""
    errors = []
    for llm in llms:
        try:
            log.info("Summarizing with %s", llm.name)
            return plugin.summarize(source, _Heartbeat(llm, store, job_id))
        except LLMUnavailable as error:
            log.warning("%s", error)
            errors.append(str(error))
    raise LLMUnavailable("No provider could answer: " + "; ".join(errors))


def backfill_source_texts(store: Store, plugins: Mapping[str, Plugin]) -> tuple[int, int]:
    """Fetch the source text of summaries that lack one, and return how many were (kept, failed).

    Makes no LLM calls and touches no notes. Running it again retries only what is still missing.
    """
    kept = failed = 0
    for name, item_id in store.summaries_without_source_text():
        log.info("Fetching %s %s", name, item_id)
        try:
            plugin = plugins[name]
            store.save_source_text(name, item_id, plugin.source_text(plugin.fetch(item_id)))
            kept += 1
        # One deleted video shouldn't stop the rest.
        except Exception as error:
            log.warning("%s %s: %s", name, item_id, error)
            failed += 1
    return kept, failed


def wait(store: Store, job_id: int, *, poll_interval: float = 1.0) -> Job:
    """Block until a job another process is running finishes, or is back in the queue to be claimed."""
    while True:
        # That process may have died, and with no server running nothing else would notice.
        store.requeue_stale(STALE_AFTER)
        job = store.get_job(job_id)
        if job.finished or job.status == "queued":
            return job
        time.sleep(poll_interval)


class Worker:
    """One background thread that runs queued jobs in order, one at a time."""

    def __init__(
        self,
        *,
        store: Store,
        plugins: Mapping[str, Plugin],
        llms: Sequence[LLM],
        vault_dir: Path,
        poll_interval: float = 1.0,
    ):
        self.store = store
        self.plugins = plugins
        self.llms = llms
        self.vault_dir = vault_dir
        self.poll_interval = poll_interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._running: Job | None = None

    def run_once(self) -> Job | None:
        """Recover abandoned jobs, then run the oldest queued job, if any. Returns it once finished."""
        requeued = self.store.requeue_stale(STALE_AFTER)
        if requeued:
            log.info("Requeued %d stale job(s)", requeued)
        job = self.store.claim()
        if job is None:
            return None
        plugin = self.plugins.get(job.plugin)
        if plugin is None:
            self.store.set_status(job.id, "failed", error=f"No plugin named {job.plugin!r}")
            return self.store.get_job(job.id)
        self._running = job
        try:
            return run(job, store=self.store, plugin=plugin, llms=self.llms, vault_dir=self.vault_dir)
        finally:
            self._running = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._loop, name="harness-worker", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        if self._thread is None:
            return
        # Wait up to (default = 5) seconds for the job to finish
        self._thread.join(timeout)
        # Still mid-job, and the thread dies with the process. Requeue it so the next start picks it up.
        running = self._running
        if self._thread.is_alive() and running is not None:
            self.store.set_status(running.id, "queued") # The next start picks up straight away
            log.info("Requeued job %d, interrupted by shutdown", running.id)

    def _loop(self) -> None:
        while not self._stop.is_set():
            if self.run_once() is None:
                self._stop.wait(self.poll_interval)
