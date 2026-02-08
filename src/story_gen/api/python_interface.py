"""Python-first interface for blueprint files and API interactions."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from story_gen.api.contracts import (
    EssayBlueprint,
    EssayCreateRequest,
    EssayEvaluateRequest,
    EssayEvaluationResponse,
    EssayResponse,
    EssayUpdateRequest,
    StoryBlueprint,
    StoryCreateRequest,
    StoryFeatureRunResponse,
    StoryResponse,
    StoryUpdateRequest,
    load_blueprint_json,
    load_essay_blueprint_json,
    save_blueprint_json,
    save_essay_blueprint_json,
)


@dataclass(frozen=True)
class AuthSession:
    """Authenticated client session."""

    access_token: str
    api_base_url: str


class StoryApiClient:
    """Tiny typed API client for Python users."""

    def __init__(self, api_base_url: str = "http://127.0.0.1:8000") -> None:
        self._api_base_url = api_base_url.rstrip("/")

    @property
    def api_base_url(self) -> str:
        return self._api_base_url

    def register(self, *, email: str, password: str, display_name: str) -> None:
        response = httpx.post(
            f"{self._api_base_url}/api/v1/auth/register",
            json={
                "email": email,
                "password": password,
                "display_name": display_name,
            },
            timeout=30.0,
        )
        response.raise_for_status()

    def login(self, *, email: str, password: str) -> AuthSession:
        response = httpx.post(
            f"{self._api_base_url}/api/v1/auth/login",
            json={"email": email, "password": password},
            timeout=30.0,
        )
        response.raise_for_status()
        payload = response.json()
        token = str(payload["access_token"])
        return AuthSession(access_token=token, api_base_url=self._api_base_url)

    def create_story(
        self,
        *,
        session: AuthSession,
        title: str,
        blueprint: StoryBlueprint,
    ) -> StoryResponse:
        request = StoryCreateRequest(title=title, blueprint=blueprint)
        response = httpx.post(
            f"{session.api_base_url}/api/v1/stories",
            json=request.model_dump(mode="json"),
            headers={"Authorization": f"Bearer {session.access_token}"},
            timeout=30.0,
        )
        response.raise_for_status()
        return StoryResponse.model_validate(response.json())

    def update_story(
        self,
        *,
        session: AuthSession,
        story_id: str,
        title: str,
        blueprint: StoryBlueprint,
    ) -> StoryResponse:
        request = StoryUpdateRequest(title=title, blueprint=blueprint)
        response = httpx.put(
            f"{session.api_base_url}/api/v1/stories/{story_id}",
            json=request.model_dump(mode="json"),
            headers={"Authorization": f"Bearer {session.access_token}"},
            timeout=30.0,
        )
        response.raise_for_status()
        return StoryResponse.model_validate(response.json())

    def extract_features(self, *, session: AuthSession, story_id: str) -> StoryFeatureRunResponse:
        response = httpx.post(
            f"{session.api_base_url}/api/v1/stories/{story_id}/features/extract",
            headers={"Authorization": f"Bearer {session.access_token}"},
            timeout=60.0,
        )
        response.raise_for_status()
        return StoryFeatureRunResponse.model_validate(response.json())

    def create_essay(
        self,
        *,
        session: AuthSession,
        title: str,
        blueprint: EssayBlueprint,
        draft_text: str = "",
    ) -> EssayResponse:
        request = EssayCreateRequest(title=title, blueprint=blueprint, draft_text=draft_text)
        response = httpx.post(
            f"{session.api_base_url}/api/v1/essays",
            json=request.model_dump(mode="json"),
            headers={"Authorization": f"Bearer {session.access_token}"},
            timeout=30.0,
        )
        response.raise_for_status()
        return EssayResponse.model_validate(response.json())

    def update_essay(
        self,
        *,
        session: AuthSession,
        essay_id: str,
        title: str,
        blueprint: EssayBlueprint,
        draft_text: str,
    ) -> EssayResponse:
        request = EssayUpdateRequest(title=title, blueprint=blueprint, draft_text=draft_text)
        response = httpx.put(
            f"{session.api_base_url}/api/v1/essays/{essay_id}",
            json=request.model_dump(mode="json"),
            headers={"Authorization": f"Bearer {session.access_token}"},
            timeout=30.0,
        )
        response.raise_for_status()
        return EssayResponse.model_validate(response.json())

    def evaluate_essay(
        self,
        *,
        session: AuthSession,
        essay_id: str,
        draft_text: str | None = None,
    ) -> EssayEvaluationResponse:
        request = EssayEvaluateRequest(draft_text=draft_text)
        response = httpx.post(
            f"{session.api_base_url}/api/v1/essays/{essay_id}/evaluate",
            json=request.model_dump(mode="json"),
            headers={"Authorization": f"Bearer {session.access_token}"},
            timeout=60.0,
        )
        response.raise_for_status()
        return EssayEvaluationResponse.model_validate(response.json())

    def latest_features(self, *, session: AuthSession, story_id: str) -> StoryFeatureRunResponse:
        response = httpx.get(
            f"{session.api_base_url}/api/v1/stories/{story_id}/features/latest",
            headers={"Authorization": f"Bearer {session.access_token}"},
            timeout=30.0,
        )
        response.raise_for_status()
        return StoryFeatureRunResponse.model_validate(response.json())


__all__ = [
    "AuthSession",
    "EssayBlueprint",
    "StoryApiClient",
    "StoryBlueprint",
    "load_blueprint_json",
    "load_essay_blueprint_json",
    "save_blueprint_json",
    "save_essay_blueprint_json",
]
