from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from story_gen.api.app import create_app


def test_health_endpoint_returns_ok_payload() -> None:
    client = TestClient(create_app())
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "story_gen"}


def test_api_stub_endpoint_returns_stage_and_endpoints() -> None:
    client = TestClient(create_app())
    response = client.get("/api/v1")
    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "story_gen"
    assert payload["stage"] == "local-preview"
    assert payload["persistence"] == "sqlite"
    assert "/healthz" in payload["endpoints"]
    assert "/api/v1/stories" in payload["endpoints"]


def test_story_crud_lifecycle(tmp_path: Path) -> None:
    db_path = tmp_path / "stories.db"
    client = TestClient(create_app(db_path=db_path))

    create = client.post(
        "/api/v1/stories",
        json={"owner_id": "alice", "title": "Chapter One", "body": "Opening beat."},
    )
    assert create.status_code == 201
    created_payload = create.json()
    story_id = created_payload["story_id"]
    assert created_payload["owner_id"] == "alice"
    assert created_payload["title"] == "Chapter One"

    fetched = client.get(f"/api/v1/stories/{story_id}")
    assert fetched.status_code == 200
    assert fetched.json()["body"] == "Opening beat."

    listed = client.get("/api/v1/stories", params={"owner_id": "alice"})
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    update = client.put(
        f"/api/v1/stories/{story_id}",
        json={"title": "Chapter One Revised", "body": "Opening beat plus revision."},
    )
    assert update.status_code == 200
    assert update.json()["title"] == "Chapter One Revised"


def test_story_endpoints_return_404_for_unknown_id(tmp_path: Path) -> None:
    client = TestClient(create_app(db_path=tmp_path / "stories.db"))
    missing_id = "does-not-exist"
    missing_get = client.get(f"/api/v1/stories/{missing_id}")
    assert missing_get.status_code == 404
    assert missing_get.json()["detail"] == "Story not found"

    missing_put = client.put(
        f"/api/v1/stories/{missing_id}",
        json={"title": "Nope", "body": "Still missing."},
    )
    assert missing_put.status_code == 404
