"""FastAPI local-preview application for story_gen."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from story_gen.adapters.sqlite_story_store import SQLiteStoryStore, StoredStory

DEFAULT_DB_PATH = Path("work/local/story_gen.db")


class HealthResponse(BaseModel):
    """Simple health payload used by probes."""

    status: Literal["ok"] = "ok"
    service: str = "story_gen"


class ApiStubResponse(BaseModel):
    """Describes currently available API capabilities and runtime mode."""

    name: str = "story_gen"
    stage: Literal["local-preview"] = "local-preview"
    persistence: Literal["sqlite"] = "sqlite"
    endpoints: list[str] = Field(
        default_factory=lambda: [
            "/healthz",
            "/api/v1",
            "/api/v1/stories",
            "/api/v1/stories/{story_id}",
        ]
    )


class StoryCreateRequest(BaseModel):
    """Request body for story creation."""

    owner_id: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1)


class StoryUpdateRequest(BaseModel):
    """Request body for story updates."""

    title: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1)


class StoryResponse(BaseModel):
    """API payload shape for persisted stories."""

    story_id: str
    owner_id: str
    title: str
    body: str
    created_at_utc: str
    updated_at_utc: str


def _story_response(story: StoredStory) -> StoryResponse:
    return StoryResponse(
        story_id=story.story_id,
        owner_id=story.owner_id,
        title=story.title,
        body=story.body,
        created_at_utc=story.created_at_utc,
        updated_at_utc=story.updated_at_utc,
    )


def _resolve_db_path(db_path: Path | None) -> Path:
    """Resolve DB path from explicit arg, env var, then default path."""
    if db_path is not None:
        return db_path
    env_value = os.environ.get("STORY_GEN_DB_PATH", "").strip()
    if env_value:
        return Path(env_value)
    return DEFAULT_DB_PATH


def create_app(db_path: Path | None = None) -> FastAPI:
    """Create the API application."""
    effective_db_path = _resolve_db_path(db_path)
    store = SQLiteStoryStore(db_path=effective_db_path)
    app = FastAPI(
        title="story_gen API",
        version="0.1.0",
        description=(
            "Local preview API for story editing and persistence. "
            "Designed for local/dev runtimes and future backend hosting."
        ),
    )

    # Keep handlers nested so this module stays the single API assembly point.
    @app.get("/healthz", response_model=HealthResponse, tags=["system"])
    def healthz() -> HealthResponse:
        return HealthResponse()

    @app.get("/api/v1", response_model=ApiStubResponse, tags=["api"])
    def api_v1_root() -> ApiStubResponse:
        return ApiStubResponse()

    @app.get("/api/v1/stories", response_model=list[StoryResponse], tags=["stories"])
    def list_stories(
        owner_id: str | None = Query(default=None, min_length=1),
        limit: int = Query(default=100, ge=1, le=500),
    ) -> list[StoryResponse]:
        return [
            _story_response(story) for story in store.list_stories(owner_id=owner_id, limit=limit)
        ]

    @app.post("/api/v1/stories", response_model=StoryResponse, tags=["stories"], status_code=201)
    def create_story(payload: StoryCreateRequest) -> StoryResponse:
        story = store.create_story(
            owner_id=payload.owner_id.strip(),
            title=payload.title.strip(),
            body=payload.body,
        )
        return _story_response(story)

    @app.get("/api/v1/stories/{story_id}", response_model=StoryResponse, tags=["stories"])
    def get_story(story_id: str) -> StoryResponse:
        story = store.get_story(story_id=story_id)
        if story is None:
            raise HTTPException(status_code=404, detail="Story not found")
        return _story_response(story)

    @app.put("/api/v1/stories/{story_id}", response_model=StoryResponse, tags=["stories"])
    def update_story(story_id: str, payload: StoryUpdateRequest) -> StoryResponse:
        story = store.update_story(
            story_id=story_id,
            title=payload.title.strip(),
            body=payload.body,
        )
        if story is None:
            raise HTTPException(status_code=404, detail="Story not found")
        return _story_response(story)

    return app


app = create_app()
