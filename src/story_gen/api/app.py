"""FastAPI local-preview application for story editing workflows."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from story_gen.adapters.sqlite_story_store import SQLiteStoryStore, StoredStory, StoredUser
from story_gen.api.contracts import (
    AuthLoginRequest,
    AuthRegisterRequest,
    AuthTokenResponse,
    StoryBlueprint,
    StoryCreateRequest,
    StoryResponse,
    StoryUpdateRequest,
    UserResponse,
)

DEFAULT_DB_PATH = Path("work/local/story_gen.db")
TOKEN_TTL_HOURS = 24
PBKDF2_ITERATIONS = 310_000


class HealthResponse(BaseModel):
    """Simple health payload used by probes."""

    status: Literal["ok"] = "ok"
    service: str = "story_gen"


class ApiRootResponse(BaseModel):
    """Describes currently available API capabilities and runtime mode."""

    name: str = "story_gen"
    stage: Literal["local-preview"] = "local-preview"
    persistence: Literal["sqlite"] = "sqlite"
    auth: Literal["bearer-token"] = "bearer-token"
    endpoints: list[str] = Field(
        default_factory=lambda: [
            "/healthz",
            "/api/v1",
            "/api/v1/auth/register",
            "/api/v1/auth/login",
            "/api/v1/me",
            "/api/v1/stories",
            "/api/v1/stories/{story_id}",
        ]
    )


def _resolve_db_path(db_path: Path | None) -> Path:
    """Resolve DB path from explicit arg, env var, then default path."""
    if db_path is not None:
        return db_path
    env_value = os.environ.get("STORY_GEN_DB_PATH", "").strip()
    if env_value:
        return Path(env_value)
    return DEFAULT_DB_PATH


def _cors_origins() -> list[str]:
    raw = os.environ.get("STORY_GEN_CORS_ORIGINS", "").strip()
    if raw:
        return [origin.strip() for origin in raw.split(",") if origin.strip()]
    return [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "https://ringxworld.github.io",
    ]


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = password_hash.split("$", maxsplit=3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    recomputed = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt_hex),
        int(iterations),
    )
    return hmac.compare_digest(recomputed.hex(), digest_hex)


def _user_response(user: StoredUser) -> UserResponse:
    return UserResponse(
        user_id=user.user_id,
        email=user.email,
        display_name=user.display_name,
        created_at_utc=user.created_at_utc,
    )


def _story_response(story: StoredStory) -> StoryResponse:
    return StoryResponse(
        story_id=story.story_id,
        owner_id=story.owner_id,
        title=story.title,
        blueprint=StoryBlueprint.model_validate_json(story.blueprint_json),
        created_at_utc=story.created_at_utc,
        updated_at_utc=story.updated_at_utc,
    )


def create_app(db_path: Path | None = None) -> FastAPI:
    """Create the API application."""
    effective_db_path = _resolve_db_path(db_path)
    store = SQLiteStoryStore(db_path=effective_db_path)
    bearer = HTTPBearer(auto_error=False)

    app = FastAPI(
        title="story_gen API",
        version="0.2.0",
        description=(
            "Local preview API for story blueprint editing and persistence. "
            "Designed for local/dev runtimes and future backend hosting."
        ),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def current_user(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    ) -> StoredUser:
        if credentials is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing bearer token",
            )
        user = store.get_user_by_token(
            token_value=credentials.credentials, now_utc=_utc_now().isoformat()
        )
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )
        return user

    @app.get("/healthz", response_model=HealthResponse, tags=["system"])
    def healthz() -> HealthResponse:
        return HealthResponse()

    @app.get("/api/v1", response_model=ApiRootResponse, tags=["api"])
    def api_v1_root() -> ApiRootResponse:
        return ApiRootResponse()

    @app.post("/api/v1/auth/register", response_model=UserResponse, tags=["auth"], status_code=201)
    def register(payload: AuthRegisterRequest) -> UserResponse:
        created = store.create_user(
            email=payload.email.strip().lower(),
            display_name=payload.display_name.strip(),
            password_hash=_hash_password(payload.password),
        )
        if created is None:
            raise HTTPException(status_code=409, detail="Email already registered")
        return _user_response(created)

    @app.post("/api/v1/auth/login", response_model=AuthTokenResponse, tags=["auth"])
    def login(payload: AuthLoginRequest) -> AuthTokenResponse:
        user = store.get_user_by_email(email=payload.email.strip().lower())
        if user is None or not _verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        expires_at = _utc_now() + timedelta(hours=TOKEN_TTL_HOURS)
        token_value = secrets.token_urlsafe(32)
        token = store.create_token(
            user_id=user.user_id,
            token_value=token_value,
            expires_at_utc=expires_at.isoformat(),
        )
        return AuthTokenResponse(
            access_token=token.token_value, expires_at_utc=token.expires_at_utc
        )

    @app.get("/api/v1/me", response_model=UserResponse, tags=["auth"])
    def me(user: StoredUser = Depends(current_user)) -> UserResponse:
        return _user_response(user)

    @app.get("/api/v1/stories", response_model=list[StoryResponse], tags=["stories"])
    def list_stories(
        limit: int = Query(default=100, ge=1, le=500),
        user: StoredUser = Depends(current_user),
    ) -> list[StoryResponse]:
        return [
            _story_response(story)
            for story in store.list_stories(owner_id=user.user_id, limit=limit)
        ]

    @app.post("/api/v1/stories", response_model=StoryResponse, tags=["stories"], status_code=201)
    def create_story(
        payload: StoryCreateRequest,
        user: StoredUser = Depends(current_user),
    ) -> StoryResponse:
        story = store.create_story(
            owner_id=user.user_id,
            title=payload.title.strip(),
            blueprint_json=payload.blueprint.model_dump_json(),
        )
        return _story_response(story)

    @app.get("/api/v1/stories/{story_id}", response_model=StoryResponse, tags=["stories"])
    def get_story(story_id: str, user: StoredUser = Depends(current_user)) -> StoryResponse:
        story = store.get_story(story_id=story_id)
        if story is None or story.owner_id != user.user_id:
            raise HTTPException(status_code=404, detail="Story not found")
        return _story_response(story)

    @app.put("/api/v1/stories/{story_id}", response_model=StoryResponse, tags=["stories"])
    def update_story(
        story_id: str,
        payload: StoryUpdateRequest,
        user: StoredUser = Depends(current_user),
    ) -> StoryResponse:
        existing = store.get_story(story_id=story_id)
        if existing is None or existing.owner_id != user.user_id:
            raise HTTPException(status_code=404, detail="Story not found")
        story = store.update_story(
            story_id=story_id,
            title=payload.title.strip(),
            blueprint_json=payload.blueprint.model_dump_json(),
        )
        if story is None:
            raise HTTPException(status_code=404, detail="Story not found")
        return _story_response(story)

    return app


app = create_app()
