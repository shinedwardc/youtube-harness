"""HTTP entry point: POST /videos queues a link, GET /jobs reports on them.

Run with: uv run uvicorn harness.api:app --host 0.0.0.0 --port 8000
"""

import logging
from contextlib import asynccontextmanager
from urllib.parse import quote, urlencode

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request, Response
from pydantic import BaseModel

from .bootstrap import Harness, build
from .core.db import Job, Summary
from .core.jobs import Worker, submit


class VideoIn(BaseModel):
    url: str


def note_url(harness: Harness, note_path: str) -> str:
    """A link that opens the note in Obsidian. Obsidian wants spaces and slashes percent-encoded."""
    query = {"vault": harness.settings.vault_name, "file": note_path}
    return "obsidian://open?" + urlencode(query, quote_via=quote, safe="")


def job_json(job: Job, harness: Harness, summary: Summary | None = None) -> dict:
    # The summary's fields only exist once a job has finished.
    data = summary.data if summary and job.status == "done" else {}
    return {
        "job_id": job.id,
        "plugin": job.plugin,
        "video_id": job.item_id,
        "input": job.input,
        "status": job.status,
        "title": data.get("title"),
        "channel": data.get("channel"),
        "category": data.get("category"),
        "tldr": data.get("tldr"),
        "tags": data.get("tags", []),
        "summarized": data.get("summarized"),
        "note_path": job.note_path,
        "note_url": note_url(harness, job.note_path) if job.note_path else None,
        "error": job.error,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }


def create_app(harness: Harness | None = None, *, start_worker: bool = True) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if harness is None:
            load_dotenv()
            logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
        app.state.harness = harness or build()
        app.state.worker = Worker(
            store=app.state.harness.store,
            plugins=app.state.harness.plugins,
            llms=app.state.harness.llms,
            vault_dir=app.state.harness.settings.vault_dir,
            poll_interval=app.state.harness.settings.poll_interval,
        )
        if start_worker:
            app.state.worker.start()
        yield
        # Docker sets SIGTERM, or uvicorn shut downs
        app.state.worker.stop()

    app = FastAPI(title="YouTube Summarizer Harness", lifespan=lifespan)

    @app.post("/videos", status_code=202)
    def submit_video(body: VideoIn, request: Request, response: Response) -> dict:
        harness: Harness = request.app.state.harness
        try:
            submission = submit(harness.store, harness.plugins["youtube"], body.url)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

        if submission.summary is not None:
            response.status_code = 200
            return {
                "video_id": submission.item_id,
                "status": "done",
                "cached": True,
                "title": submission.summary.data.get("title"),
                "note_path": submission.summary.note_path,
                "note_url": note_url(harness, submission.summary.note_path),
            }
        return {**job_json(submission.job, harness), "cached": False}

    @app.get("/jobs")
    def list_jobs(request: Request, limit: int = Query(50, ge=1, le=1000)) -> dict:
        harness: Harness = request.app.state.harness
        summaries = harness.store.summaries()
        jobs = harness.store.recent_jobs(limit)
        return {"jobs": [job_json(job, harness, summaries.get((job.plugin, job.item_id))) for job in jobs]}

    @app.get("/jobs/{job_id}")
    def get_job(job_id: int, request: Request) -> dict:
        harness: Harness = request.app.state.harness
        job = harness.store.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail=f"No job {job_id}")
        return job_json(job, harness, harness.store.get_summary(job.plugin, job.item_id))

    return app


app = create_app()
