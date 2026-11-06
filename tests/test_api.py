"""POST /videos and GET /jobs/{id}, with the worker driven by hand."""

import pytest
from fastapi.testclient import TestClient

from harness.api import create_app
from harness.bootstrap import Harness
from harness.core.config import Settings
from tests.conftest import FakeLLM

URL = "https://youtu.be/dQw4w9WgXcQ"


@pytest.fixture
def client(store, plugin, vault):
    harness = Harness(
        settings=Settings(vault_dir=vault, db_path=store.path, summary_language="auto", poll_interval=0.1),
        store=store,
        plugins={"youtube": plugin},
        llms=[FakeLLM()],
    )
    with TestClient(create_app(harness, start_worker=False)) as client:
        yield client


def test_post_queues_a_job_and_get_reports_it_done(client):
    response = client.post("/videos", json={"url": URL})
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued" and body["video_id"] == "dQw4w9WgXcQ" and body["cached"] is False

    client.app.state.worker.run_once()

    job = client.get(f"/jobs/{body['job_id']}").json()
    assert job["status"] == "done"
    assert job["note_path"].startswith("youtube/")


def test_a_summarized_video_returns_200_from_the_cache(client):
    client.post("/videos", json={"url": URL})
    client.app.state.worker.run_once()

    response = client.post("/videos", json={"url": URL})

    assert response.status_code == 200
    assert response.json()["cached"] is True


def test_an_invalid_link_is_a_422(client):
    response = client.post("/videos", json={"url": "https://vimeo.com/1"})
    assert response.status_code == 422
    assert "Not a YouTube video link" in response.json()["detail"]


def test_an_unknown_job_is_a_404(client):
    assert client.get("/jobs/999").status_code == 404
