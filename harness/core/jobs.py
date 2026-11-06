"""Submitting, running and polling jobs. Phase 2 replaces Worker with the custom scheduler."""

import logging
import threading
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from .db import ACTIVE_STATUSES, Job, Store, Summary
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
    """Take a claimed job through fetch, summarize and write. Never raises; the outcome is in the job."""
    try:
        cached = store.get_summary(plugin.name, job.item_id)
        if cached is not None:
            # Another job finished this item after ours was queued.
            store.finish(job, cached.note_path)
            return store.get_job(job.id)

        log.info("Fetching %s %s", plugin.name, job.item_id)
        source = plugin.fetch(job.item_id)

        store.set_status(job.id, "summarizing")
        data = _summarize(plugin, source, llms)

        store.set_status(job.id, "writing")
        note_path = plugin.write(data, vault_dir)
        store.finish(job, str(note_path), data)
        log.info("Wrote %s", note_path)
    # `outcome` marks how the job ended, so a caller that reports that itself (the CLI) can skip these.
    except Unprocessable as error:
        log.warning("%s %s: %s", plugin.name, job.item_id, error, extra={"outcome": True})
        store.set_status(job.id, error.status, error=str(error))
    except Exception as error:
        log.exception("Job %d failed", job.id, extra={"outcome": True})
        store.set_status(job.id, "failed", error=f"{type(error).__name__}: {error}")
    return store.get_job(job.id)


def _summarize(plugin: Plugin, source, llms: Sequence[LLM]) -> dict:
    """Try each provider in order. Only an unavailable provider moves on to the next."""
    errors = []
    for llm in llms:
        try:
            log.info("Summarizing with %s", llm.name)
            return plugin.summarize(source, llm)
        except LLMUnavailable as error:
            log.warning("%s", error)
            errors.append(str(error))
    raise LLMUnavailable("No provider could answer: " + "; ".join(errors))


def wait(store: Store, job_id: int, *, poll_interval: float = 1.0) -> Job:
    """Block until a job another process is running finishes."""
    while True:
        job = store.get_job(job_id)
        if job.status not in ACTIVE_STATUSES:
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

    def run_once(self) -> Job | None:
        """Run the oldest queued job, if any. Returns it once finished."""
        job = self.store.claim()
        if job is None:
            return None
        plugin = self.plugins.get(job.plugin)
        if plugin is None:
            self.store.set_status(job.id, "failed", error=f"No plugin named {job.plugin!r}")
            return self.store.get_job(job.id)
        return run(job, store=self.store, plugin=plugin, llms=self.llms, vault_dir=self.vault_dir)

    def start(self) -> None:
        requeued = self.store.requeue_stale(STALE_AFTER)
        if requeued:
            log.info("Requeued %d stale job(s)", requeued)
        self._thread = threading.Thread(target=self._loop, name="harness-worker", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout)

    def _loop(self) -> None:
        while not self._stop.is_set():
            if self.run_once() is None:
                self._stop.wait(self.poll_interval)
