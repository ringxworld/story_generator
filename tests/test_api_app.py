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


def _sample_essay_blueprint() -> dict[str, Any]:
    return {
        "prompt": "Argue for constraint-first drafting.",
        "policy": {
            "thesis_statement": "Constraint-first drafting improves coherence.",
            "audience": "technical readers",
            "tone": "analytical",
            "min_words": 100,
            "max_words": 900,
            "required_sections": [
                {
                    "key": "introduction",
                    "purpose": "Frame claim",
                    "min_paragraphs": 1,
                    "required_terms": [],
                },
                {
                    "key": "analysis",
                    "purpose": "Defend claim",
                    "min_paragraphs": 1,
                    "required_terms": [],
                },
                {
                    "key": "conclusion",
                    "purpose": "Synthesize claim",
                    "min_paragraphs": 1,
                    "required_terms": [],
                },
            ],
            "banned_phrases": ["as an ai language model"],
            "required_citations": 1,
        },
        "rubric": ["clear thesis", "evidence per claim"],
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
    assert "/api/v1/stories/{story_id}/features/extract" in payload["endpoints"]
    assert "/api/v1/essays" in payload["endpoints"]
    assert "/api/v1/essays/{essay_id}/evaluate" in payload["endpoints"]


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

    latest_before_extract = client.get(
        f"/api/v1/stories/{story_id}/features/latest", headers=headers
    )
    assert latest_before_extract.status_code == 404

    extracted = client.post(f"/api/v1/stories/{story_id}/features/extract", headers=headers)
    assert extracted.status_code == 200
    extracted_payload = extracted.json()
    assert extracted_payload["story_id"] == story_id
    assert extracted_payload["schema_version"] == "story_features.v1"
    assert extracted_payload["chapter_features"]

    latest = client.get(f"/api/v1/stories/{story_id}/features/latest", headers=headers)
    assert latest.status_code == 200
    assert latest.json()["run_id"] == extracted_payload["run_id"]


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
    bob_extract = client.post(f"/api/v1/stories/{story_id}/features/extract", headers=bob_headers)
    bob_latest = client.get(f"/api/v1/stories/{story_id}/features/latest", headers=bob_headers)
    assert bob_get.status_code == 404
    assert bob_put.status_code == 404
    assert bob_extract.status_code == 404
    assert bob_latest.status_code == 404


def test_essay_crud_and_evaluation_lifecycle(tmp_path: Path) -> None:
    client = TestClient(create_app(db_path=tmp_path / "stories.db"))
    headers = _auth_headers(client, "alice@example.com")

    create = client.post(
        "/api/v1/essays",
        headers=headers,
        json={
            "title": "Constraint Drafting",
            "blueprint": _sample_essay_blueprint(),
            "draft_text": (
                "introduction: Constraint-first drafting improves coherence.\n\n"
                "analysis: according to [1], explicit checks reduce drift.\n\n"
                "conclusion: constraints preserve intent."
            ),
        },
    )
    assert create.status_code == 201
    essay_id = create.json()["essay_id"]

    listed = client.get("/api/v1/essays", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    fetched = client.get(f"/api/v1/essays/{essay_id}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["title"] == "Constraint Drafting"

    updated = client.put(
        f"/api/v1/essays/{essay_id}",
        headers=headers,
        json={
            "title": "Constraint Drafting Revised",
            "blueprint": _sample_essay_blueprint(),
            "draft_text": (
                "introduction: Constraint-first drafting improves coherence.\n\n"
                "analysis: according to [1], explicit checks reduce drift.\n\n"
                "conclusion: constraints preserve intent and maintain quality."
            ),
        },
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Constraint Drafting Revised"

    evaluated = client.post(
        f"/api/v1/essays/{essay_id}/evaluate",
        headers=headers,
        json={},
    )
    assert evaluated.status_code == 200
    payload = evaluated.json()
    assert payload["essay_id"] == essay_id
    assert payload["required_citations"] == 1
    assert payload["word_count"] > 0
    assert isinstance(payload["checks"], list)


def test_essay_access_is_isolated_by_owner(tmp_path: Path) -> None:
    client = TestClient(create_app(db_path=tmp_path / "stories.db"))
    alice_headers = _auth_headers(client, "alice@example.com")
    bob_headers = _auth_headers(client, "bob@example.com")

    created = client.post(
        "/api/v1/essays",
        headers=alice_headers,
        json={
            "title": "Alice Essay",
            "blueprint": _sample_essay_blueprint(),
            "draft_text": "introduction: hello",
        },
    )
    assert created.status_code == 201
    essay_id = created.json()["essay_id"]

    bob_get = client.get(f"/api/v1/essays/{essay_id}", headers=bob_headers)
    bob_put = client.put(
        f"/api/v1/essays/{essay_id}",
        headers=bob_headers,
        json={
            "title": "Hijack",
            "blueprint": _sample_essay_blueprint(),
            "draft_text": "x",
        },
    )
    bob_evaluate = client.post(
        f"/api/v1/essays/{essay_id}/evaluate",
        headers=bob_headers,
        json={},
    )
    assert bob_get.status_code == 404
    assert bob_put.status_code == 404
    assert bob_evaluate.status_code == 404


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


def test_register_rejects_invalid_email_and_weak_password(tmp_path: Path) -> None:
    client = TestClient(create_app(db_path=tmp_path / "stories.db"))
    bad_email = client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "password123", "display_name": "Alice"},
    )
    weak_password = client.post(
        "/api/v1/auth/register",
        json={"email": "alice@example.com", "password": "allletters", "display_name": "Alice"},
    )
    assert bad_email.status_code == 422
    assert weak_password.status_code == 422


def test_story_create_rejects_invalid_blueprint_invariants(tmp_path: Path) -> None:
    client = TestClient(create_app(db_path=tmp_path / "stories.db"))
    headers = _auth_headers(client, "alice@example.com")

    invalid_blueprint = _sample_blueprint()
    invalid_blueprint["chapters"] = [
        {
            "key": "ch01",
            "title": "Chapter 1",
            "objective": "x",
            "required_themes": ["missing-theme"],
            "participating_characters": ["rhea"],
            "prerequisites": ["ch02"],
            "draft_text": None,
        },
        {
            "key": "ch02",
            "title": "Chapter 2",
            "objective": "y",
            "required_themes": ["memory"],
            "participating_characters": ["rhea"],
            "prerequisites": ["ch01"],
            "draft_text": None,
        },
    ]

    response = client.post(
        "/api/v1/stories",
        headers=headers,
        json={"title": "Broken Blueprint", "blueprint": invalid_blueprint},
    )
    assert response.status_code == 422


def test_feature_extract_rejects_story_without_chapters(tmp_path: Path) -> None:
    client = TestClient(create_app(db_path=tmp_path / "stories.db"))
    headers = _auth_headers(client, "alice@example.com")

    empty_chapters_blueprint = _sample_blueprint()
    empty_chapters_blueprint["chapters"] = []
    created = client.post(
        "/api/v1/stories",
        headers=headers,
        json={"title": "No Chapters", "blueprint": empty_chapters_blueprint},
    )
    assert created.status_code == 201
    story_id = created.json()["story_id"]

    extracted = client.post(f"/api/v1/stories/{story_id}/features/extract", headers=headers)
    assert extracted.status_code == 422
