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
from story_gen.cli.pipeline_batch import build_arg_parser, run_pipeline_batch


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
        register = client.post(
            "/api/v1/auth/register",
            json={
                "email": "e2e@example.com",
                "password": "password123",
                "display_name": "E2E",
            },
        )
        assert register.status_code == 201

        login = client.post(
            "/api/v1/auth/login",
            json={"email": "e2e@example.com", "password": "password123"},
        )
        assert login.status_code == 200
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

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


def test_re_zero_pipeline_batch_optional(tmp_path: Path) -> None:
    resource_root = Path("work/resources/re_zero/n2267be/chapters")
    if not resource_root.exists():
        pytest.skip("Re:Zero chapter resources not available")
    if os.environ.get("STORY_GEN_E2E_REZERO", "").lower() not in {"1", "true", "yes"}:
        pytest.skip("Set STORY_GEN_E2E_REZERO=1 to enable Re:Zero batch test")

    output_dir = tmp_path / "pipeline_runs"
    parser = build_arg_parser()
    args = parser.parse_args(
        [
            "--source-dir",
            str(resource_root),
            "--output-dir",
            str(output_dir),
            "--run-id",
            "re-zero-e2e",
            "--max-chapters",
            "2",
            "--translate-provider",
            "none",
            "--mode",
            "analyze",
        ]
    )
    summary = run_pipeline_batch(args)
    assert summary.processed_chapters >= 1
