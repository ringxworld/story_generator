from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from story_gen.api.contracts import (
    EssayBlueprint,
    StoryBlueprint,
    load_blueprint_json,
    load_essay_blueprint_json,
    save_blueprint_json,
    save_essay_blueprint_json,
)
from story_gen.api.python_interface import AuthSession, StoryApiClient


def _blueprint() -> StoryBlueprint:
    return StoryBlueprint(
        premise="Premise",
        themes=[],
        characters=[],
        chapters=[],
        canon_rules=[],
    )


def test_blueprint_json_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "blueprint.json"
    save_blueprint_json(path, _blueprint())
    loaded = load_blueprint_json(path)
    assert loaded.premise == "Premise"


def test_story_api_client_login_parses_token(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post(url: str, json: object, timeout: float) -> httpx.Response:
        request = httpx.Request("POST", url)
        if str(url).endswith("/auth/login"):
            return httpx.Response(
                status_code=200,
                request=request,
                json={"access_token": "token-123", "token_type": "bearer", "expires_at_utc": "x"},
            )
        return httpx.Response(status_code=201, request=request, json={})

    monkeypatch.setattr("story_gen.api.python_interface.httpx.post", fake_post)
    client = StoryApiClient(api_base_url="http://127.0.0.1:8000")
    session = client.login(email="alice@example.com", password="password123")
    assert session.access_token == "token-123"


def test_essay_blueprint_json_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "essay_blueprint.json"
    blueprint = EssayBlueprint.model_validate(
        {
            "prompt": "Write with constraints.",
            "policy": {
                "thesis_statement": "Constraints reduce drift.",
                "audience": "technical readers",
                "tone": "analytical",
                "min_words": 100,
                "max_words": 400,
                "required_sections": [
                    {
                        "key": "introduction",
                        "purpose": "Frame claim",
                        "min_paragraphs": 1,
                        "required_terms": [],
                    }
                ],
                "banned_phrases": [],
                "required_citations": 1,
            },
            "rubric": ["clear thesis"],
        }
    )
    save_essay_blueprint_json(path, blueprint)
    loaded = load_essay_blueprint_json(path)
    assert loaded.prompt == "Write with constraints."


def test_story_api_client_feature_methods(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post(
        url: str,
        json: object | None = None,
        headers: dict[str, str] | None = None,
        timeout: float = 30.0,
    ) -> httpx.Response:
        del json, headers, timeout
        request = httpx.Request("POST", url)
        if str(url).endswith("/features/extract"):
            return httpx.Response(
                status_code=200,
                request=request,
                json={
                    "run_id": "run-1",
                    "story_id": "story-1",
                    "owner_id": "owner-1",
                    "schema_version": "story_features.v1",
                    "extracted_at_utc": "2026-01-01T00:00:00+00:00",
                    "chapter_features": [
                        {
                            "schema_version": "story_features.v1",
                            "story_id": "story-1",
                            "chapter_key": "ch01",
                            "chapter_index": 1,
                            "source_length_chars": 100,
                            "sentence_count": 3,
                            "token_count": 20,
                            "avg_sentence_length": 6.66,
                            "dialogue_line_ratio": 0.33,
                            "top_keywords": ["memory"],
                        }
                    ],
                },
            )
        return httpx.Response(status_code=404, request=request)

    def fake_get(
        url: str, headers: dict[str, str] | None = None, timeout: float = 30.0
    ) -> httpx.Response:
        del headers, timeout
        request = httpx.Request("GET", url)
        return httpx.Response(
            status_code=200,
            request=request,
            json={
                "run_id": "run-1",
                "story_id": "story-1",
                "owner_id": "owner-1",
                "schema_version": "story_features.v1",
                "extracted_at_utc": "2026-01-01T00:00:00+00:00",
                "chapter_features": [
                    {
                        "schema_version": "story_features.v1",
                        "story_id": "story-1",
                        "chapter_key": "ch01",
                        "chapter_index": 1,
                        "source_length_chars": 100,
                        "sentence_count": 3,
                        "token_count": 20,
                        "avg_sentence_length": 6.66,
                        "dialogue_line_ratio": 0.33,
                        "top_keywords": ["memory"],
                    }
                ],
            },
        )

    monkeypatch.setattr("story_gen.api.python_interface.httpx.post", fake_post)
    monkeypatch.setattr("story_gen.api.python_interface.httpx.get", fake_get)

    client = StoryApiClient(api_base_url="http://127.0.0.1:8000")
    session = AuthSession(access_token="token-123", api_base_url="http://127.0.0.1:8000")
    extracted = client.extract_features(session=session, story_id="story-1")
    latest = client.latest_features(session=session, story_id="story-1")
    assert extracted.run_id == "run-1"
    assert latest.chapter_features[0].chapter_key == "ch01"


def test_story_api_client_essay_methods(monkeypatch: pytest.MonkeyPatch) -> None:
    blueprint = EssayBlueprint.model_validate(
        {
            "prompt": "Write with constraints.",
            "policy": {
                "thesis_statement": "Constraints reduce drift.",
                "audience": "technical readers",
                "tone": "analytical",
                "min_words": 100,
                "max_words": 400,
                "required_sections": [
                    {
                        "key": "introduction",
                        "purpose": "Frame claim",
                        "min_paragraphs": 1,
                        "required_terms": [],
                    }
                ],
                "banned_phrases": [],
                "required_citations": 1,
            },
            "rubric": ["clear thesis"],
        }
    )

    def fake_post(
        url: str,
        json: object | None = None,
        headers: dict[str, str] | None = None,
        timeout: float = 30.0,
    ) -> httpx.Response:
        del headers, timeout
        request = httpx.Request("POST", url)
        if str(url).endswith("/api/v1/essays"):
            return httpx.Response(
                status_code=201,
                request=request,
                json={
                    "essay_id": "essay-1",
                    "owner_id": "owner-1",
                    "title": "Essay",
                    "blueprint": blueprint.model_dump(mode="json"),
                    "draft_text": "introduction: according to [1]...",
                    "created_at_utc": "2026-01-01T00:00:00+00:00",
                    "updated_at_utc": "2026-01-01T00:00:00+00:00",
                },
            )
        if str(url).endswith("/api/v1/essays/essay-1/evaluate"):
            assert json is not None
            return httpx.Response(
                status_code=200,
                request=request,
                json={
                    "essay_id": "essay-1",
                    "owner_id": "owner-1",
                    "passed": True,
                    "score": 92.0,
                    "word_count": 300,
                    "citation_count": 1,
                    "required_citations": 1,
                    "checks": [],
                },
            )
        return httpx.Response(status_code=404, request=request)

    def fake_put(
        url: str,
        json: object | None = None,
        headers: dict[str, str] | None = None,
        timeout: float = 30.0,
    ) -> httpx.Response:
        del json, headers, timeout
        request = httpx.Request("PUT", url)
        return httpx.Response(
            status_code=200,
            request=request,
            json={
                "essay_id": "essay-1",
                "owner_id": "owner-1",
                "title": "Essay v2",
                "blueprint": blueprint.model_dump(mode="json"),
                "draft_text": "introduction: according to [1]...",
                "created_at_utc": "2026-01-01T00:00:00+00:00",
                "updated_at_utc": "2026-01-01T01:00:00+00:00",
            },
        )

    monkeypatch.setattr("story_gen.api.python_interface.httpx.post", fake_post)
    monkeypatch.setattr("story_gen.api.python_interface.httpx.put", fake_put)

    client = StoryApiClient(api_base_url="http://127.0.0.1:8000")
    session = AuthSession(access_token="token-123", api_base_url="http://127.0.0.1:8000")
    created = client.create_essay(
        session=session,
        title="Essay",
        blueprint=blueprint,
        draft_text="introduction: according to [1]...",
    )
    updated = client.update_essay(
        session=session,
        essay_id=created.essay_id,
        title="Essay v2",
        blueprint=blueprint,
        draft_text="introduction: according to [1]...",
    )
    evaluated = client.evaluate_essay(session=session, essay_id=created.essay_id)

    assert created.essay_id == "essay-1"
    assert updated.title == "Essay v2"
    assert evaluated.passed is True
