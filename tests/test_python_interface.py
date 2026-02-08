from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from story_gen.api.contracts import StoryBlueprint, load_blueprint_json, save_blueprint_json
from story_gen.api.python_interface import StoryApiClient


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
