from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from story_gen.adapters.sqlite_anomaly_store import SQLiteAnomalyStore
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


def test_swagger_redoc_and_openapi_endpoints_are_available() -> None:
    client = TestClient(create_app())
    swagger = client.get("/docs")
    redoc = client.get("/redoc")
    openapi = client.get("/openapi.json")
    assert swagger.status_code == 200
    assert "Swagger UI" in swagger.text
    assert redoc.status_code == 200
    assert "ReDoc" in redoc.text
    assert openapi.status_code == 200
    payload = openapi.json()
    assert payload["info"]["title"] == "story_gen API"
    assert any(tag["name"] == "auth" for tag in payload["tags"])


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
    assert "/api/v1/stories/{story_id}/analysis/run" in payload["endpoints"]
    assert "/api/v1/stories/{story_id}/dashboard/overview" in payload["endpoints"]
    assert "/api/v1/stories/{story_id}/dashboard/v1/overview" in payload["endpoints"]
    assert "/api/v1/stories/{story_id}/dashboard/v1/timeline" in payload["endpoints"]
    assert "/api/v1/stories/{story_id}/dashboard/v1/themes/heatmap" in payload["endpoints"]
    assert "/api/v1/stories/{story_id}/dashboard/graph/export.png" in payload["endpoints"]
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

    latest_analysis_before_run = client.get(
        f"/api/v1/stories/{story_id}/analysis/latest", headers=headers
    )
    assert latest_analysis_before_run.status_code == 404

    analysis_run = client.post(
        f"/api/v1/stories/{story_id}/analysis/run",
        headers=headers,
        json={},
    )
    assert analysis_run.status_code == 200
    analysis_payload = analysis_run.json()
    assert analysis_payload["story_id"] == story_id
    assert analysis_payload["schema_version"] == "story_analysis.v1"
    assert analysis_payload["event_count"] >= 1

    latest_analysis = client.get(f"/api/v1/stories/{story_id}/analysis/latest", headers=headers)
    assert latest_analysis.status_code == 200
    assert latest_analysis.json()["run_id"] == analysis_payload["run_id"]

    overview = client.get(f"/api/v1/stories/{story_id}/dashboard/overview", headers=headers)
    assert overview.status_code == 200
    assert overview.json()["events_count"] >= 1
    versioned_overview = client.get(
        f"/api/v1/stories/{story_id}/dashboard/v1/overview", headers=headers
    )
    assert versioned_overview.status_code == 200
    assert versioned_overview.json() == overview.json()

    timeline = client.get(f"/api/v1/stories/{story_id}/dashboard/timeline", headers=headers)
    assert timeline.status_code == 200
    assert isinstance(timeline.json(), list)
    assert len(timeline.json()) >= 1
    versioned_timeline = client.get(
        f"/api/v1/stories/{story_id}/dashboard/v1/timeline", headers=headers
    )
    assert versioned_timeline.status_code == 200
    assert versioned_timeline.json() == timeline.json()

    heatmap = client.get(f"/api/v1/stories/{story_id}/dashboard/themes/heatmap", headers=headers)
    assert heatmap.status_code == 200
    assert isinstance(heatmap.json(), list)
    versioned_heatmap = client.get(
        f"/api/v1/stories/{story_id}/dashboard/v1/themes/heatmap", headers=headers
    )
    assert versioned_heatmap.status_code == 200
    assert versioned_heatmap.json() == heatmap.json()

    arcs = client.get(f"/api/v1/stories/{story_id}/dashboard/arcs", headers=headers)
    assert arcs.status_code == 200
    assert isinstance(arcs.json(), list)

    graph = client.get(f"/api/v1/stories/{story_id}/dashboard/graph", headers=headers)
    assert graph.status_code == 200
    graph_payload = graph.json()
    assert isinstance(graph_payload["nodes"], list)
    assert isinstance(graph_payload["edges"], list)
    assert graph_payload["nodes"][0].get("layout_x") is not None
    assert graph_payload["nodes"][0].get("layout_y") is not None

    graph_export = client.get(
        f"/api/v1/stories/{story_id}/dashboard/graph/export.svg", headers=headers
    )
    assert graph_export.status_code == 200
    assert graph_export.json()["format"] == "svg"
    assert graph_export.json()["svg"].startswith("<svg")
    graph_export_png = client.get(
        f"/api/v1/stories/{story_id}/dashboard/graph/export.png", headers=headers
    )
    assert graph_export_png.status_code == 200
    png_payload = graph_export_png.json()
    assert png_payload["format"] == "png"
    assert isinstance(png_payload["png_base64"], str)
    assert png_payload["png_base64"]
    graph_export_png_second = client.get(
        f"/api/v1/stories/{story_id}/dashboard/graph/export.png", headers=headers
    )
    assert graph_export_png_second.status_code == 200
    assert graph_export_png_second.json()["png_base64"] == png_payload["png_base64"]

    drilldown = client.get(
        f"/api/v1/stories/{story_id}/dashboard/drilldown/missing-item",
        headers=headers,
    )
    assert drilldown.status_code == 404


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
    bob_analysis_run = client.post(
        f"/api/v1/stories/{story_id}/analysis/run", headers=bob_headers, json={}
    )
    bob_analysis_latest = client.get(
        f"/api/v1/stories/{story_id}/analysis/latest", headers=bob_headers
    )
    bob_dashboard = client.get(
        f"/api/v1/stories/{story_id}/dashboard/overview", headers=bob_headers
    )
    bob_versioned_dashboard = client.get(
        f"/api/v1/stories/{story_id}/dashboard/v1/overview", headers=bob_headers
    )
    assert bob_get.status_code == 404
    assert bob_put.status_code == 404
    assert bob_extract.status_code == 404
    assert bob_latest.status_code == 404
    assert bob_analysis_run.status_code == 404
    assert bob_analysis_latest.status_code == 404
    assert bob_dashboard.status_code == 404
    assert bob_versioned_dashboard.status_code == 404


def test_story_analysis_accepts_custom_source_text(tmp_path: Path) -> None:
    client = TestClient(create_app(db_path=tmp_path / "stories.db"))
    headers = _auth_headers(client, "alice@example.com")
    create = client.post(
        "/api/v1/stories",
        headers=headers,
        json={"title": "Spanish Story", "blueprint": _sample_blueprint()},
    )
    assert create.status_code == 201
    story_id = create.json()["story_id"]

    run = client.post(
        f"/api/v1/stories/{story_id}/analysis/run",
        headers=headers,
        json={
            "source_text": "La historia revela la memoria familiar.",
            "source_type": "text",
            "target_language": "en",
        },
    )
    assert run.status_code == 200
    payload = run.json()
    assert payload["source_language"] == "es"


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


def test_api_startup_prunes_anomaly_store(tmp_path: Path, monkeypatch: Any) -> None:
    calls: dict[str, int] = {}

    def fake_prune(self: SQLiteAnomalyStore, *, retention_days: int, max_rows: int) -> int:
        calls["retention_days"] = retention_days
        calls["max_rows"] = max_rows
        return 0

    monkeypatch.setenv("STORY_GEN_ANOMALY_RETENTION_DAYS", "45")
    monkeypatch.setenv("STORY_GEN_ANOMALY_MAX_ROWS", "2500")
    monkeypatch.setattr(SQLiteAnomalyStore, "prune_anomalies", fake_prune)
    with TestClient(create_app(db_path=tmp_path / "stories.db")) as client:
        response = client.get("/healthz")
    assert response.status_code == 200
    assert calls == {"retention_days": 45, "max_rows": 2500}


def test_analysis_quality_failure_is_persisted_as_anomaly(tmp_path: Path) -> None:
    db_path = tmp_path / "stories.db"
    client = TestClient(create_app(db_path=db_path))
    headers = _auth_headers(client, "alice@example.com")

    created = client.post(
        "/api/v1/stories",
        headers=headers,
        json={"title": "Risky Analysis", "blueprint": _sample_blueprint()},
    )
    assert created.status_code == 201
    story_id = created.json()["story_id"]

    run = client.post(
        f"/api/v1/stories/{story_id}/analysis/run",
        headers=headers,
        json={"source_text": "これは危険だ。スバルは記憶の断片を追いかける。"},
    )
    assert run.status_code == 200
    assert run.json()["quality_gate"]["passed"] is False

    anomalies = SQLiteAnomalyStore(db_path=db_path).list_recent(limit=20)
    quality_failures = [event for event in anomalies if event.code == "quality_gate_failed"]
    assert quality_failures
    assert story_id in quality_failures[0].metadata_json


def test_dashboard_payload_shape_error_records_anomaly(tmp_path: Path) -> None:
    import sqlite3

    db_path = tmp_path / "stories.db"
    client = TestClient(create_app(db_path=db_path))
    headers = _auth_headers(client, "alice@example.com")
    created = client.post(
        "/api/v1/stories",
        headers=headers,
        json={"title": "Dashboard Corruption", "blueprint": _sample_blueprint()},
    )
    assert created.status_code == 201
    story_id = created.json()["story_id"]
    run = client.post(
        f"/api/v1/stories/{story_id}/analysis/run",
        headers=headers,
        json={},
    )
    assert run.status_code == 200

    with sqlite3.connect(str(db_path)) as connection:
        connection.execute(
            """
            UPDATE story_analysis_runs
            SET dashboard_json = ?
            WHERE story_id = ?
            """,
            ('{"overview": []}', story_id),
        )
        connection.commit()

    bad_response = client.get(f"/api/v1/stories/{story_id}/dashboard/overview", headers=headers)
    assert bad_response.status_code == 500
    assert bad_response.json()["detail"] == "Invalid dashboard overview payload"
    versioned_bad_response = client.get(
        f"/api/v1/stories/{story_id}/dashboard/v1/overview", headers=headers
    )
    assert versioned_bad_response.status_code == 500
    assert versioned_bad_response.json()["detail"] == "Invalid dashboard overview payload"

    anomalies = SQLiteAnomalyStore(db_path=db_path).list_recent(limit=20)
    payload_errors = [event for event in anomalies if event.code == "invalid_payload_shape"]
    assert payload_errors
    assert "overview" in payload_errors[0].metadata_json
