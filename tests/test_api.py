"""POST /videos, GET /jobs and the web page, with the worker driven by hand."""

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
        settings=Settings(
            vault_dir=vault,
            db_path=store.path,
            summary_language="auto",
            poll_interval=0.1,
            vault_name="My Vault",
        ),
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


def test_job_list_is_newest_first_and_respects_the_limit(client):
    client.post("/videos", json={"url": "https://youtu.be/aaaaaaaaaaa"})
    client.post("/videos", json={"url": "https://youtu.be/bbbbbbbbbbb"})

    jobs = client.get("/jobs").json()["jobs"]
    assert [job["video_id"] for job in jobs] == ["bbbbbbbbbbb", "aaaaaaaaaaa"]

    jobs = client.get("/jobs", params={"limit": 1}).json()["jobs"]
    assert [job["video_id"] for job in jobs] == ["bbbbbbbbbbb"]


@pytest.mark.parametrize("limit", [0, 1001])
def test_job_list_rejects_a_limit_out_of_range(client, limit):
    assert client.get("/jobs", params={"limit": limit}).status_code == 422


def test_job_list_is_empty_before_any_link_is_sent(client):
    assert client.get("/jobs").json() == {"jobs": []}


def test_a_queued_job_has_no_title_or_note_link_yet(client):
    client.post("/videos", json={"url": URL})

    job = client.get("/jobs").json()["jobs"][0]

    assert job["status"] == "queued"
    assert job["input"] == URL
    assert job["title"] is None and job["channel"] is None and job["note_url"] is None
    assert job["category"] is None and job["tldr"] is None and job["tags"] == []
    assert job["highlights"] == [] and job["key_points"] == [] and job["timestamps"] == []
    assert job["summarized"] is None


def test_a_finished_job_has_its_title_and_an_obsidian_link(client):
    client.post("/videos", json={"url": URL})
    client.app.state.worker.run_once()

    job = client.get("/jobs").json()["jobs"][0]

    assert job["title"] == "How Raft Works"
    assert job["channel"] == "Example Channel"
    assert job["category"] == "Education"
    assert job["tldr"] == "Raft elects a leader and replicates a log."
    assert job["tags"] == ["distributed-systems", "consensus"]
    # The shelf shows these under the thumbnail.
    assert job["highlights"] == ["Leaders win by majority vote", "Leaders replicate the log"]
    # The page's detail panel shows all of these without opening the note.
    assert job["key_points"] == ["A leader is elected by majority vote.", "The leader replicates log entries."]
    assert job["timestamps"] == [{"time": "00:00", "label": "Intro"}, {"time": "01:00", "label": "Leader election"}]
    month_folder = job["note_path"].split("/")[1]
    # The page's month rows and the vault's month folders come from the same date.
    assert job["summarized"].startswith(month_folder)
    assert job["note_url"] == (
        f"obsidian://open?vault=My%20Vault&file=youtube%2F{month_folder}%2Fhow-raft-works-dQw4w9WgXcQ.md"
    )


def test_a_single_job_has_the_same_summary_fields_as_the_list(client):
    client.post("/videos", json={"url": URL})
    client.app.state.worker.run_once()

    listed = client.get("/jobs").json()["jobs"][0]

    assert client.get(f"/jobs/{listed['job_id']}").json() == listed


def test_a_cached_reply_has_the_title_and_obsidian_link_too(client):
    client.post("/videos", json={"url": URL})
    client.app.state.worker.run_once()

    body = client.post("/videos", json={"url": URL}).json()

    assert body["title"] == "How Raft Works"
    assert body["note_url"].startswith("obsidian://open?vault=My%20Vault&file=youtube%2F")


def test_the_page_is_served_at_the_root(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.headers["cache-control"] == "no-cache"
    assert "<title>Video notes</title>" in response.text


def test_vault_name_defaults_to_the_vault_folder():
    settings = Settings.from_env({"HARNESS_VAULT_DIR": "/mnt/c/Users/me/Obsidian Vault"})
    assert settings.vault_name == "Obsidian Vault"


def test_vault_name_can_be_set_for_a_mounted_vault():
    settings = Settings.from_env({"HARNESS_VAULT_DIR": "/vault", "HARNESS_VAULT_NAME": "Obsidian Vault"})
    assert settings.vault_name == "Obsidian Vault"
