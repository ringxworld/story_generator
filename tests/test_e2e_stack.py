from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest

from story_gen.api.contracts import EssayBlueprint, StoryBlueprint
from story_gen.api.python_interface import StoryApiClient


def _auth_headers(client: httpx.Client, *, email: str, display_name: str) -> dict[str, str]:
    register = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "password123",
            "display_name": display_name,
        },
    )
    assert register.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "password123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_health(base_url: str, timeout_seconds: float = 12.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            response = httpx.get(f"{base_url}/healthz", timeout=1.0)
            if response.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.2)
    raise RuntimeError(f"Timed out waiting for API health at {base_url}/healthz")


def _story_blueprint() -> dict[str, Any]:
    return {
        "premise": "A city uncovers rewritten history.",
        "themes": [{"key": "memory", "statement": "Memory is contestable.", "priority": 1}],
        "characters": [
            {
                "key": "rhea",
                "role": "investigator",
                "motivation": "Find the missing ledger.",
                "voice_markers": [],
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
                "draft_text": "Rhea checked the archive and found a contradiction.",
            }
        ],
        "canon_rules": ["No supernatural causes."],
    }


def _essay_blueprint() -> dict[str, Any]:
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


@pytest.fixture()
def e2e_api_base_url(tmp_path: Path) -> Iterator[str]:
    port = _find_free_port()
    db_path = tmp_path / "e2e.db"
    env = os.environ.copy()
    env["STORY_GEN_DB_PATH"] = str(db_path)
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "story_gen.api.app:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    base_url = f"http://127.0.0.1:{port}"
    try:
        _wait_for_health(base_url)
        if process.poll() is not None:
            output = process.stdout.read() if process.stdout is not None else ""
            raise RuntimeError(f"E2E API process exited early.\n{output}")
        yield base_url
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def test_e2e_story_and_essay_http_flows(e2e_api_base_url: str) -> None:
    with httpx.Client(base_url=e2e_api_base_url, timeout=30.0) as client:
        headers = _auth_headers(client, email="e2e@example.com", display_name="E2E")

        created_story = client.post(
            "/api/v1/stories",
            headers=headers,
            json={"title": "E2E Story", "blueprint": _story_blueprint()},
        )
        assert created_story.status_code == 201
        story_id = created_story.json()["story_id"]

        extracted = client.post(f"/api/v1/stories/{story_id}/features/extract", headers=headers)
        assert extracted.status_code == 200
        assert extracted.json()["chapter_features"]

        created_essay = client.post(
            "/api/v1/essays",
            headers=headers,
            json={
                "title": "E2E Essay",
                "blueprint": _essay_blueprint(),
                "draft_text": (
                    "introduction: Constraint-first drafting improves coherence.\n\n"
                    "analysis: according to [1], explicit checks reduce drift.\n\n"
                    "conclusion: constraints preserve intent."
                ),
            },
        )
        assert created_essay.status_code == 201
        essay_id = created_essay.json()["essay_id"]

        evaluated = client.post(f"/api/v1/essays/{essay_id}/evaluate", headers=headers, json={})
        assert evaluated.status_code == 200
        assert evaluated.json()["score"] >= 0


def test_e2e_live_stack_analysis_and_dashboard_http_flow(e2e_api_base_url: str) -> None:
    with httpx.Client(base_url=e2e_api_base_url, timeout=30.0) as client:
        alice_headers = _auth_headers(
            client,
            email="qa-e2e-alice@example.com",
            display_name="QA E2E Alice",
        )
        bob_headers = _auth_headers(
            client,
            email="qa-e2e-bob@example.com",
            display_name="QA E2E Bob",
        )

        created_story = client.post(
            "/api/v1/stories",
            headers=alice_headers,
            json={"title": "Live Stack Dashboard E2E", "blueprint": _story_blueprint()},
        )
        assert created_story.status_code == 201
        story_id = created_story.json()["story_id"]

        # Unauthenticated dashboard access must be rejected.
        unauthorized_overview = client.get(f"/api/v1/stories/{story_id}/dashboard/overview")
        assert unauthorized_overview.status_code == 401

        analysis_run = client.post(
            f"/api/v1/stories/{story_id}/analysis/run",
            headers=alice_headers,
            json={},
        )
        assert analysis_run.status_code == 200
        assert analysis_run.json()["event_count"] >= 1

        overview = client.get(
            f"/api/v1/stories/{story_id}/dashboard/overview", headers=alice_headers
        )
        assert overview.status_code == 200
        assert overview.json()["events_count"] >= 1

        timeline = client.get(
            f"/api/v1/stories/{story_id}/dashboard/timeline", headers=alice_headers
        )
        assert timeline.status_code == 200
        assert isinstance(timeline.json(), list)
        assert timeline.json()

        heatmap = client.get(
            f"/api/v1/stories/{story_id}/dashboard/themes/heatmap",
            headers=alice_headers,
        )
        assert heatmap.status_code == 200
        assert isinstance(heatmap.json(), list)

        arcs = client.get(f"/api/v1/stories/{story_id}/dashboard/arcs", headers=alice_headers)
        assert arcs.status_code == 200
        assert isinstance(arcs.json(), list)

        graph = client.get(f"/api/v1/stories/{story_id}/dashboard/graph", headers=alice_headers)
        assert graph.status_code == 200
        graph_payload = graph.json()
        assert isinstance(graph_payload["nodes"], list)
        assert graph_payload["nodes"]
        assert isinstance(graph_payload["edges"], list)

        drilldown_status_codes: list[int] = []
        candidate_item_ids: list[str] = []
        for node in graph_payload["nodes"]:
            node_id = node.get("id")
            node_group = node.get("group")
            if not isinstance(node_id, str):
                continue
            if node_group == "theme":
                candidate_item_ids.append(f"theme:{node_id}")
            candidate_item_ids.append(node_id)
        assert candidate_item_ids

        for item_id in candidate_item_ids:
            drilldown = client.get(
                f"/api/v1/stories/{story_id}/dashboard/drilldown/{item_id}",
                headers=alice_headers,
            )
            drilldown_status_codes.append(drilldown.status_code)
            if drilldown.status_code == 200:
                payload = drilldown.json()
                assert payload["item_id"] == item_id
                break
        assert 200 in drilldown_status_codes

        timeline_export_svg_first = client.get(
            f"/api/v1/stories/{story_id}/dashboard/timeline/export.svg",
            headers=alice_headers,
        )
        assert timeline_export_svg_first.status_code == 200
        svg_payload = timeline_export_svg_first.json()
        assert svg_payload["format"] == "svg"
        assert svg_payload["svg"].startswith("<svg")
        timeline_export_svg_second = client.get(
            f"/api/v1/stories/{story_id}/dashboard/timeline/export.svg",
            headers=alice_headers,
        )
        assert timeline_export_svg_second.status_code == 200
        assert timeline_export_svg_second.json()["svg"] == svg_payload["svg"]

        graph_export_png_first = client.get(
            f"/api/v1/stories/{story_id}/dashboard/graph/export.png",
            headers=alice_headers,
        )
        assert graph_export_png_first.status_code == 200
        png_payload = graph_export_png_first.json()
        assert png_payload["format"] == "png"
        assert png_payload["png_base64"]
        graph_export_png_second = client.get(
            f"/api/v1/stories/{story_id}/dashboard/graph/export.png",
            headers=alice_headers,
        )
        assert graph_export_png_second.status_code == 200
        assert graph_export_png_second.json()["png_base64"] == png_payload["png_base64"]

        # Cross-user route access is owner-isolated and intentionally returns 404.
        cross_user_overview = client.get(
            f"/api/v1/stories/{story_id}/dashboard/overview",
            headers=bob_headers,
        )
        assert cross_user_overview.status_code == 404


def test_e2e_python_client_flow(e2e_api_base_url: str) -> None:
    api = StoryApiClient(api_base_url=e2e_api_base_url)
    api.register(
        email="python-client@example.com",
        password="password123",
        display_name="Python Client",
    )
    session = api.login(email="python-client@example.com", password="password123")
    story_blueprint = StoryBlueprint.model_validate(_story_blueprint())
    essay_blueprint = EssayBlueprint.model_validate(_essay_blueprint())

    created_story = api.create_story(
        session=session,
        title="Python Client Story",
        blueprint=story_blueprint,
    )
    extracted = api.extract_features(session=session, story_id=created_story.story_id)
    created_essay = api.create_essay(
        session=session,
        title="Python Client Essay",
        blueprint=essay_blueprint,
        draft_text=(
            "introduction: Constraint-first drafting improves coherence.\n\n"
            "analysis: according to [1], explicit checks reduce drift.\n\n"
            "conclusion: constraints preserve intent."
        ),
    )
    evaluated = api.evaluate_essay(session=session, essay_id=created_essay.essay_id)

    assert created_story.story_id
    assert extracted.chapter_features
    assert created_essay.essay_id
    assert evaluated.score >= 0
