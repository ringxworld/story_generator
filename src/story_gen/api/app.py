"""FastAPI application stub for story_gen."""

from __future__ import annotations

from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Simple health payload used by probes."""

    status: Literal["ok"] = "ok"
    service: str = "story_gen"


class ApiStubResponse(BaseModel):
    """Describes currently available API capabilities."""

    name: str = "story_gen"
    stage: Literal["stub"] = "stub"
    endpoints: list[str] = Field(default_factory=lambda: ["/healthz", "/api/v1"])


def create_app() -> FastAPI:
    """Create the API application."""
    app = FastAPI(
        title="story_gen API",
        version="0.1.0",
        description="Stub API for story ingestion and planning workflows.",
    )

    @app.get("/healthz", response_model=HealthResponse, tags=["system"])
    def healthz() -> HealthResponse:
        return HealthResponse()

    @app.get("/api/v1", response_model=ApiStubResponse, tags=["api"])
    def api_v1_root() -> ApiStubResponse:
        return ApiStubResponse()

    return app


app = create_app()
