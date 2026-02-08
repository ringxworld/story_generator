from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from story_gen.api.app import create_app


def _sample_blueprint() -> dict[str, Any]:
    return {
        "premise": "A city uncovers rewritten history.",
        "themes": [{"key": "memory", "statement": "Memory is contestable.", "priority": 1}],
        "characters": [
            {
                "key": "rhea",
                "role": "investigator",
                "motivation": "Find the missing ledger.",
                "voice_markers": ["short questions"],
                "relationships": {},
            }
        ],
        "chapters": [
            {
                "key": "ch01",
                "title": "The Missing Ledger",
                "objective": "Introduce contradiction.",
                "required_themes": ["memory"],
                "participating_characters": ["rhea"],
                "prerequisites": [],
                "draft_text": None,
            }
        ],
        "canon_rules": ["No supernatural causes."],
    }


def _auth_headers(client: TestClient, email: str) -> dict[str, str]:
    register = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "display_name": "Alice"},
    )
    assert register.status_code == 201
    login = client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health_endpoint_returns_ok_payload() -> None:
    client = TestClient(create_app())
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "story_gen"}


def test_api_root_reports_auth_and_story_endpoints() -> None:
    client = TestClient(create_app())
    response = client.get("/api/v1")
    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "story_gen"
    assert payload["stage"] == "local-preview"
    assert payload["persistence"] == "sqlite"
    assert payload["auth"] == "bearer-token"
    assert "/api/v1/auth/register" in payload["endpoints"]
    assert "/api/v1/stories" in payload["endpoints"]


def test_api_includes_cors_headers_for_local_studio_origin(tmp_path: Path) -> None:
    client = TestClient(create_app(db_path=tmp_path / "stories.db"))
    response = client.options(
        "/api/v1",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://127.0.0.1:5173"


def test_story_crud_requires_authentication(tmp_path: Path) -> None:
    client = TestClient(create_app(db_path=tmp_path / "stories.db"))
    unauthorized = client.get("/api/v1/stories")
    assert unauthorized.status_code == 401


def test_story_crud_lifecycle_with_auth(tmp_path: Path) -> None:
    client = TestClient(create_app(db_path=tmp_path / "stories.db"))
    headers = _auth_headers(client, "alice@example.com")

    create = client.post(
        "/api/v1/stories",
        headers=headers,
        json={"title": "Chapter Plan", "blueprint": _sample_blueprint()},
    )
    assert create.status_code == 201
    created_payload = create.json()
    story_id = created_payload["story_id"]
    assert created_payload["title"] == "Chapter Plan"
    assert created_payload["blueprint"]["premise"] == _sample_blueprint()["premise"]

    fetched = client.get(f"/api/v1/stories/{story_id}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["story_id"] == story_id

    listed = client.get("/api/v1/stories", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    update = client.put(
        f"/api/v1/stories/{story_id}",
        headers=headers,
        json={"title": "Chapter Plan Revised", "blueprint": _sample_blueprint()},
    )
    assert update.status_code == 200
    assert update.json()["title"] == "Chapter Plan Revised"


def test_story_access_is_isolated_by_owner(tmp_path: Path) -> None:
    client = TestClient(create_app(db_path=tmp_path / "stories.db"))
    alice_headers = _auth_headers(client, "alice@example.com")
    bob_headers = _auth_headers(client, "bob@example.com")
    created = client.post(
        "/api/v1/stories",
        headers=alice_headers,
        json={"title": "Alice Story", "blueprint": _sample_blueprint()},
    )
    story_id = created.json()["story_id"]

    bob_get = client.get(f"/api/v1/stories/{story_id}", headers=bob_headers)
    bob_put = client.put(
        f"/api/v1/stories/{story_id}",
        headers=bob_headers,
        json={"title": "Hijack", "blueprint": _sample_blueprint()},
    )
    assert bob_get.status_code == 404
    assert bob_put.status_code == 404


def test_register_and_login_failure_paths(tmp_path: Path) -> None:
    client = TestClient(create_app(db_path=tmp_path / "stories.db"))
    first = client.post(
        "/api/v1/auth/register",
        json={"email": "alice@example.com", "password": "password123", "display_name": "Alice"},
    )
    duplicate = client.post(
        "/api/v1/auth/register",
        json={"email": "alice@example.com", "password": "password123", "display_name": "Alice"},
    )
    bad_login = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "wrong-password"},
    )
    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert bad_login.status_code == 401
