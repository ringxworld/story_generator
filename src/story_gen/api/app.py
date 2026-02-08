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

from story_gen.adapters.sqlite_essay_store import SQLiteEssayStore, StoredEssay
from story_gen.adapters.sqlite_feature_store import SQLiteFeatureStore, StoredFeatureRun
from story_gen.adapters.sqlite_story_store import SQLiteStoryStore, StoredStory, StoredUser
from story_gen.api.contracts import (
    AuthLoginRequest,
    AuthRegisterRequest,
    AuthTokenResponse,
    ChapterBlock,
    EssayBlueprint,
    EssayCreateRequest,
    EssayEvaluateRequest,
    EssayEvaluationResponse,
    EssayQualityCheckResponse,
    EssayResponse,
    EssaySectionRequirement,
    EssayUpdateRequest,
    StoryBlueprint,
    StoryCreateRequest,
    StoryFeatureRowResponse,
    StoryFeatureRunResponse,
    StoryResponse,
    StoryUpdateRequest,
    UserResponse,
)
from story_gen.core.essay_quality import (
    EssayDraftInput,
    EssayPolicySpec,
    EssaySectionSpec,
    evaluate_essay_quality,
)
from story_gen.core.story_feature_pipeline import (
    ChapterFeatureInput,
    StoryFeatureExtractionResult,
    extract_story_features,
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
            "/api/v1/stories/{story_id}/features/extract",
            "/api/v1/stories/{story_id}/features/latest",
            "/api/v1/essays",
            "/api/v1/essays/{essay_id}",
            "/api/v1/essays/{essay_id}/evaluate",
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


def _essay_response(essay: StoredEssay) -> EssayResponse:
    return EssayResponse(
        essay_id=essay.essay_id,
        owner_id=essay.owner_id,
        title=essay.title,
        blueprint=EssayBlueprint.model_validate_json(essay.blueprint_json),
        draft_text=essay.draft_text,
        created_at_utc=essay.created_at_utc,
        updated_at_utc=essay.updated_at_utc,
    )


def _section_spec(section: EssaySectionRequirement) -> EssaySectionSpec:
    return EssaySectionSpec(
        key=section.key,
        purpose=section.purpose,
        min_paragraphs=section.min_paragraphs,
        required_terms=tuple(section.required_terms),
    )


def _policy_spec(blueprint: EssayBlueprint) -> EssayPolicySpec:
    return EssayPolicySpec(
        thesis_statement=blueprint.policy.thesis_statement,
        audience=blueprint.policy.audience,
        tone=blueprint.policy.tone,
        min_words=blueprint.policy.min_words,
        max_words=blueprint.policy.max_words,
        required_sections=tuple(
            _section_spec(section) for section in blueprint.policy.required_sections
        ),
        banned_phrases=tuple(blueprint.policy.banned_phrases),
        required_citations=blueprint.policy.required_citations,
    )


def _chapter_input_from_blueprint(chapter: ChapterBlock) -> ChapterFeatureInput:
    source_text = chapter.draft_text or chapter.objective
    return ChapterFeatureInput(
        chapter_key=chapter.key,
        title=chapter.title,
        text=source_text,
    )


def _feature_run_response(
    *,
    run: StoredFeatureRun,
    result: StoryFeatureExtractionResult,
) -> StoryFeatureRunResponse:
    return StoryFeatureRunResponse(
        run_id=run.run_id,
        story_id=run.story_id,
        owner_id=run.owner_id,
        schema_version=run.schema_version,
        extracted_at_utc=run.extracted_at_utc,
        chapter_features=[
            StoryFeatureRowResponse(
                schema_version=row.schema_version,
                story_id=row.story_id,
                chapter_key=row.chapter_key,
                chapter_index=row.chapter_index,
                source_length_chars=row.source_length_chars,
                sentence_count=row.sentence_count,
                token_count=row.token_count,
                avg_sentence_length=row.avg_sentence_length,
                dialogue_line_ratio=row.dialogue_line_ratio,
                top_keywords=row.top_keywords,
            )
            for row in result.chapter_features
        ],
    )


def create_app(db_path: Path | None = None) -> FastAPI:
    """Create the API application."""
    effective_db_path = _resolve_db_path(db_path)
    store = SQLiteStoryStore(db_path=effective_db_path)
    feature_store = SQLiteFeatureStore(db_path=effective_db_path)
    essay_store = SQLiteEssayStore(db_path=effective_db_path)
    bearer = HTTPBearer(auto_error=False)

    app = FastAPI(
        title="story_gen API",
        version="0.3.0",
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
            email=payload.email,
            display_name=payload.display_name.strip(),
            password_hash=_hash_password(payload.password.get_secret_value()),
        )
        if created is None:
            raise HTTPException(status_code=409, detail="Email already registered")
        return _user_response(created)

    @app.post("/api/v1/auth/login", response_model=AuthTokenResponse, tags=["auth"])
    def login(payload: AuthLoginRequest) -> AuthTokenResponse:
        user = store.get_user_by_email(email=payload.email)
        if user is None or not _verify_password(
            payload.password.get_secret_value(), user.password_hash
        ):
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

    @app.post(
        "/api/v1/stories/{story_id}/features/extract",
        response_model=StoryFeatureRunResponse,
        tags=["stories", "features"],
    )
    def extract_features(
        story_id: str, user: StoredUser = Depends(current_user)
    ) -> StoryFeatureRunResponse:
        story = store.get_story(story_id=story_id)
        if story is None or story.owner_id != user.user_id:
            raise HTTPException(status_code=404, detail="Story not found")
        blueprint = StoryBlueprint.model_validate_json(story.blueprint_json)
        chapters = [_chapter_input_from_blueprint(chapter) for chapter in blueprint.chapters]
        if not chapters:
            raise HTTPException(
                status_code=422,
                detail="Story must include at least one chapter to extract features.",
            )
        result = extract_story_features(story_id=story.story_id, chapters=chapters)
        run = feature_store.write_feature_result(owner_id=user.user_id, result=result)
        return _feature_run_response(run=run, result=result)

    @app.get(
        "/api/v1/stories/{story_id}/features/latest",
        response_model=StoryFeatureRunResponse,
        tags=["stories", "features"],
    )
    def get_latest_features(
        story_id: str,
        user: StoredUser = Depends(current_user),
    ) -> StoryFeatureRunResponse:
        story = store.get_story(story_id=story_id)
        if story is None or story.owner_id != user.user_id:
            raise HTTPException(status_code=404, detail="Story not found")
        latest = feature_store.get_latest_feature_result(
            owner_id=user.user_id, story_id=story.story_id
        )
        if latest is None:
            raise HTTPException(status_code=404, detail="Feature run not found")
        run, result = latest
        return _feature_run_response(run=run, result=result)

    @app.get("/api/v1/essays", response_model=list[EssayResponse], tags=["essays"])
    def list_essays(
        limit: int = Query(default=100, ge=1, le=500),
        user: StoredUser = Depends(current_user),
    ) -> list[EssayResponse]:
        return [
            _essay_response(essay)
            for essay in essay_store.list_essays(owner_id=user.user_id, limit=limit)
        ]

    @app.post("/api/v1/essays", response_model=EssayResponse, tags=["essays"], status_code=201)
    def create_essay(
        payload: EssayCreateRequest,
        user: StoredUser = Depends(current_user),
    ) -> EssayResponse:
        essay = essay_store.create_essay(
            owner_id=user.user_id,
            title=payload.title.strip(),
            blueprint_json=payload.blueprint.model_dump_json(),
            draft_text=payload.draft_text,
        )
        return _essay_response(essay)

    @app.get("/api/v1/essays/{essay_id}", response_model=EssayResponse, tags=["essays"])
    def get_essay(essay_id: str, user: StoredUser = Depends(current_user)) -> EssayResponse:
        essay = essay_store.get_essay(essay_id=essay_id)
        if essay is None or essay.owner_id != user.user_id:
            raise HTTPException(status_code=404, detail="Essay not found")
        return _essay_response(essay)

    @app.put("/api/v1/essays/{essay_id}", response_model=EssayResponse, tags=["essays"])
    def update_essay(
        essay_id: str,
        payload: EssayUpdateRequest,
        user: StoredUser = Depends(current_user),
    ) -> EssayResponse:
        existing = essay_store.get_essay(essay_id=essay_id)
        if existing is None or existing.owner_id != user.user_id:
            raise HTTPException(status_code=404, detail="Essay not found")
        updated = essay_store.update_essay(
            essay_id=essay_id,
            title=payload.title.strip(),
            blueprint_json=payload.blueprint.model_dump_json(),
            draft_text=payload.draft_text,
        )
        if updated is None:
            raise HTTPException(status_code=404, detail="Essay not found")
        return _essay_response(updated)

    @app.post(
        "/api/v1/essays/{essay_id}/evaluate",
        response_model=EssayEvaluationResponse,
        tags=["essays"],
    )
    def evaluate_essay(
        essay_id: str,
        payload: EssayEvaluateRequest,
        user: StoredUser = Depends(current_user),
    ) -> EssayEvaluationResponse:
        essay = essay_store.get_essay(essay_id=essay_id)
        if essay is None or essay.owner_id != user.user_id:
            raise HTTPException(status_code=404, detail="Essay not found")

        blueprint = EssayBlueprint.model_validate_json(essay.blueprint_json)
        draft_text = payload.draft_text if payload.draft_text is not None else essay.draft_text
        result = evaluate_essay_quality(
            EssayDraftInput(
                title=essay.title,
                prompt=blueprint.prompt,
                draft_text=draft_text,
                policy=_policy_spec(blueprint),
            )
        )
        return EssayEvaluationResponse(
            essay_id=essay.essay_id,
            owner_id=essay.owner_id,
            passed=result.passed,
            score=result.score,
            word_count=result.word_count,
            citation_count=result.citation_count,
            required_citations=blueprint.policy.required_citations,
            checks=[
                EssayQualityCheckResponse(
                    code=check.code,
                    severity=check.severity,
                    message=check.message,
                )
                for check in result.checks
            ],
        )

    return app


app = create_app()
