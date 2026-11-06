"""SQLite storage for jobs and the summary cache. Safe to share between the CLI and the server."""

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Statuses a job passes through while some process is working on it.
ACTIVE_STATUSES = ("queued", "fetching", "summarizing", "writing")
_ACTIVE_SQL = ", ".join(f"'{status}'" for status in ACTIVE_STATUSES)

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS jobs (
    id          INTEGER PRIMARY KEY,
    plugin      TEXT NOT NULL,
    item_id     TEXT NOT NULL,
    input       TEXT NOT NULL,
    status      TEXT NOT NULL,
    error       TEXT,
    note_path   TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

-- At most one unfinished job per item, so a link sent twice is worked on once.
CREATE UNIQUE INDEX IF NOT EXISTS jobs_one_active
    ON jobs (plugin, item_id) WHERE status IN ({_ACTIVE_SQL});

CREATE TABLE IF NOT EXISTS summaries (
    plugin      TEXT NOT NULL,
    item_id     TEXT NOT NULL,
    note_path   TEXT NOT NULL,
    data        TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    PRIMARY KEY (plugin, item_id)
);

-- The full text each summary was made from, for search and Q&A. Kept out of `summaries`
-- because it is large and GET /jobs reads every summary on each poll.
CREATE TABLE IF NOT EXISTS source_texts (
    plugin      TEXT NOT NULL,
    item_id     TEXT NOT NULL,
    text        TEXT NOT NULL,
    fetched_at  TEXT NOT NULL,
    PRIMARY KEY (plugin, item_id)
);
"""

_SAVE_SOURCE_TEXT = "INSERT OR REPLACE INTO source_texts (plugin, item_id, text, fetched_at) VALUES (?, ?, ?, ?)"


@dataclass(frozen=True)
class Job:
    id: int
    plugin: str
    item_id: str
    input: str
    status: str
    error: str | None
    note_path: str | None
    created_at: str
    updated_at: str

    @property
    def finished(self) -> bool:
        return self.status not in ACTIVE_STATUSES


@dataclass(frozen=True)
class Summary:
    plugin: str
    item_id: str
    note_path: str
    data: dict
    created_at: str


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class Store:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            # WAL lets the API read while the worker or the CLI writes.
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript(SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """A short-lived connection per operation, so any thread can use the Store."""
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    # --- summaries (the cache) ---

    def get_summary(self, plugin: str, item_id: str) -> Summary | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM summaries WHERE plugin = ? AND item_id = ?", (plugin, item_id)
            ).fetchone()
        if row is None:
            return None
        return Summary(**{**dict(row), "data": json.loads(row["data"])})

    def summaries(self) -> dict[tuple[str, str], Summary]:
        """Every summary, keyed by plugin and item. One query, for listing many jobs at once."""
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM summaries").fetchall()
        return {
            (row["plugin"], row["item_id"]): Summary(**{**dict(row), "data": json.loads(row["data"])})
            for row in rows
        }

    # --- source texts ---

    def get_source_text(self, plugin: str, item_id: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT text FROM source_texts WHERE plugin = ? AND item_id = ?", (plugin, item_id)
            ).fetchone()
        return row["text"] if row else None

    def save_source_text(self, plugin: str, item_id: str, text: str) -> None:
        with self._connect() as conn:
            conn.execute(_SAVE_SOURCE_TEXT, (plugin, item_id, text, _now()))

    def summaries_without_source_text(self) -> list[tuple[str, str]]:
        """The (plugin, item ID) of every summary whose source text isn't stored, oldest first."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT plugin, item_id FROM summaries"
                " WHERE NOT EXISTS (SELECT 1 FROM source_texts"
                " WHERE source_texts.plugin = summaries.plugin AND source_texts.item_id = summaries.item_id)"
                " ORDER BY created_at"
            ).fetchall()
        return [(row["plugin"], row["item_id"]) for row in rows]

    # --- jobs ---

    def create_job(self, plugin: str, item_id: str, raw_input: str) -> Job:
        """Queue a job, or return the unfinished one already queued for this item."""
        now = _now()
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "INSERT INTO jobs (plugin, item_id, input, status, created_at, updated_at)"
                    " VALUES (?, ?, ?, 'queued', ?, ?) RETURNING *",
                    (plugin, item_id, raw_input, now, now),
                ).fetchone()
            return Job(**row)
        except sqlite3.IntegrityError:
            active = self.active_job(plugin, item_id)
            if active is None:
                # It finished between the insert and this lookup; queue a fresh one.
                return self.create_job(plugin, item_id, raw_input)
            return active

    def active_job(self, plugin: str, item_id: str) -> Job | None:
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT * FROM jobs WHERE plugin = ? AND item_id = ? AND status IN ({_ACTIVE_SQL})",
                (plugin, item_id),
            ).fetchone()
        return Job(**row) if row else None

    def get_job(self, job_id: int) -> Job | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return Job(**row) if row else None

    def recent_jobs(self, limit: int) -> list[Job]:
        """The newest jobs first."""
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM jobs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [Job(**row) for row in rows]

    def claim(self, job_id: int | None = None) -> Job | None:
        """Atomically move a queued job to `fetching`. Two processes can never claim the same job."""
        if job_id is None:
            where, params = "id = (SELECT id FROM jobs WHERE status = 'queued' ORDER BY id LIMIT 1)", ()
        else:
            where, params = "id = ? AND status = 'queued'", (job_id,)
        with self._connect() as conn:
            row = conn.execute(
                f"UPDATE jobs SET status = 'fetching', updated_at = ? WHERE {where} RETURNING *",
                (_now(), *params),
            ).fetchone()
        return Job(**row) if row else None

    def set_status(self, job_id: int, status: str, *, error: str | None = None) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE jobs SET status = ?, error = ?, updated_at = ? WHERE id = ?",
                (status, error, _now(), job_id),
            )

    def touch(self, job_id: int) -> None:
        """Record that a job is still being worked on, so requeue_stale leaves it alone."""
        with self._connect() as conn:
            conn.execute("UPDATE jobs SET updated_at = ? WHERE id = ?", (_now(), job_id))

    def finish(
        self, job: Job, note_path: str, data: dict | None = None, *, source_text: str | None = None
    ) -> None:
        """Mark the job done and store any new summary and source text, in one transaction."""
        now = _now()
        with self._connect() as conn:
            if data is not None:
                conn.execute(
                    "INSERT OR REPLACE INTO summaries (plugin, item_id, note_path, data, created_at)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (job.plugin, job.item_id, note_path, json.dumps(data, ensure_ascii=False), now),
                )
            if source_text is not None:
                conn.execute(_SAVE_SOURCE_TEXT, (job.plugin, job.item_id, source_text, now))
            conn.execute(
                "UPDATE jobs SET status = 'done', error = NULL, note_path = ?, updated_at = ? WHERE id = ?",
                (note_path, now, job.id),
            )

    def requeue_stale(self, older_than: timedelta) -> int:
        """Put back jobs whose process died mid-run. Returns how many were requeued."""
        cutoff = (datetime.now(UTC) - older_than).isoformat(timespec="seconds")
        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE jobs SET status = 'queued', updated_at = ?"
                " WHERE status IN ('fetching', 'summarizing', 'writing') AND updated_at < ?",
                (_now(), cutoff),
            )
        return cursor.rowcount
