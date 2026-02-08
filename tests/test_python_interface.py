from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from story_gen.api.contracts import StoryBlueprint, load_blueprint_json, save_blueprint_json
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
