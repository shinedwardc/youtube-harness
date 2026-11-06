"""HTTP entry point: POST /videos queues a link, GET /jobs/{id} reports on it.

Run with: uv run uvicorn harness.api:app --host 0.0.0.0 --port 8000
"""

import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel

from .bootstrap import Harness, build
from .core.db import Job
from .core.jobs import Worker, submit


class VideoIn(BaseModel):
    url: str


def job_json(job: Job) -> dict:
    return {
        "job_id": job.id,
        "plugin": job.plugin,
        "video_id": job.item_id,
        "status": job.status,
        "note_path": job.note_path,
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
                "note_path": submission.summary.note_path,
            }
        return {**job_json(submission.job), "cached": False}

    @app.get("/jobs/{job_id}")
    def get_job(job_id: int, request: Request) -> dict:
        job = request.app.state.harness.store.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail=f"No job {job_id}")
        return job_json(job)

    return app


app = create_app()
