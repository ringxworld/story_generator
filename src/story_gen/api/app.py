"""FastAPI local-preview application for story editing workflows."""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal, cast

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from story_gen.adapters.sqlite_anomaly_store import SQLiteAnomalyStore
from story_gen.adapters.sqlite_essay_store import SQLiteEssayStore, StoredEssay
from story_gen.adapters.sqlite_feature_store import SQLiteFeatureStore, StoredFeatureRun
from story_gen.adapters.sqlite_story_analysis_store import (
    SQLiteStoryAnalysisStore,
    StoredAnalysisRun,
)
from story_gen.adapters.sqlite_story_store import SQLiteStoryStore, StoredStory, StoredUser
from story_gen.api.contracts import (
    AuthLoginRequest,
    AuthRegisterRequest,
    AuthTokenResponse,
    ChapterBlock,
    DashboardArcPointResponse,
    DashboardDrilldownResponse,
    DashboardGraphEdgeResponse,
    DashboardGraphExportResponse,
    DashboardGraphNodeResponse,
    DashboardGraphPngExportResponse,
    DashboardGraphResponse,
    DashboardOverviewResponse,
    DashboardThemeHeatmapCellResponse,
    DashboardTimelineLaneResponse,
    EssayBlueprint,
    EssayCreateRequest,
    EssayEvaluateRequest,
    EssayEvaluationResponse,
    EssayQualityCheckResponse,
    EssayResponse,
    EssaySectionRequirement,
    EssayUpdateRequest,
    StoryAnalysisGateResponse,
    StoryAnalysisRunRequest,
    StoryAnalysisRunResponse,
    StoryBlueprint,
    StoryCreateRequest,
    StoryFeatureRowResponse,
    StoryFeatureRunResponse,
    StoryResponse,
    StoryUpdateRequest,
    UserResponse,
)
from story_gen.core.dashboard_views import GraphEdge, GraphNode, export_graph_png
from story_gen.core.essay_quality import (
    EssayDraftInput,
    EssayPolicySpec,
    EssaySectionSpec,
    evaluate_essay_quality,
)
from story_gen.core.story_analysis_pipeline import run_story_analysis
from story_gen.core.story_feature_pipeline import (
    ChapterFeatureInput,
    StoryFeatureExtractionResult,
    extract_story_features,
)
from story_gen.core.story_schema import StoryDocument, StoryStage

DEFAULT_DB_PATH = Path("work/local/story_gen.db")
TOKEN_TTL_HOURS = 24
PBKDF2_ITERATIONS = 310_000

logger = logging.getLogger(__name__)


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
            "/api/v1/stories/{story_id}/analysis/run",
            "/api/v1/stories/{story_id}/analysis/latest",
            "/api/v1/stories/{story_id}/dashboard/overview",
            "/api/v1/stories/{story_id}/dashboard/v1/overview",
            "/api/v1/stories/{story_id}/dashboard/timeline",
            "/api/v1/stories/{story_id}/dashboard/v1/timeline",
            "/api/v1/stories/{story_id}/dashboard/themes/heatmap",
            "/api/v1/stories/{story_id}/dashboard/v1/themes/heatmap",
            "/api/v1/stories/{story_id}/dashboard/arcs",
            "/api/v1/stories/{story_id}/dashboard/drilldown/{item_id}",
            "/api/v1/stories/{story_id}/dashboard/graph",
            "/api/v1/stories/{story_id}/dashboard/graph/export.svg",
            "/api/v1/stories/{story_id}/dashboard/graph/export.png",
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


def _int_env(name: str, default: int, *, minimum: int, maximum: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(minimum, min(maximum, value))


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


def _analysis_source_text(blueprint: StoryBlueprint) -> str:
    chunks: list[str] = []
    for chapter in blueprint.chapters:
        text = chapter.draft_text.strip() if chapter.draft_text else chapter.objective.strip()
        if text:
            chunks.append(f"{chapter.title}. {text}")
    if chunks:
        return "\n\n".join(chunks)
    return blueprint.premise


def _analysis_summary_response(
    *,
    run: StoredAnalysisRun,
    document: StoryDocument,
) -> StoryAnalysisRunResponse:
    return StoryAnalysisRunResponse(
        run_id=run.run_id,
        story_id=run.story_id,
        owner_id=run.owner_id,
        schema_version=run.schema_version,
        analyzed_at_utc=run.analyzed_at_utc,
        source_language=document.source_language,
        target_language=document.target_language,
        segment_count=len(document.raw_segments),
        event_count=len(document.extracted_events),
        beat_count=len(document.story_beats),
        theme_count=len(document.theme_signals),
        insight_count=len(document.insights),
        quality_gate=StoryAnalysisGateResponse(
            passed=document.quality_gate.passed,
            confidence_floor=document.quality_gate.confidence_floor,
            hallucination_risk=document.quality_gate.hallucination_risk,
            translation_quality=document.quality_gate.translation_quality,
            reasons=document.quality_gate.reasons,
        ),
    )


def create_app(db_path: Path | None = None) -> FastAPI:
    """Create the API application."""
    effective_db_path = _resolve_db_path(db_path)
    store = SQLiteStoryStore(db_path=effective_db_path)
    feature_store = SQLiteFeatureStore(db_path=effective_db_path)
    analysis_store = SQLiteStoryAnalysisStore(db_path=effective_db_path)
    essay_store = SQLiteEssayStore(db_path=effective_db_path)
    anomaly_store = SQLiteAnomalyStore(db_path=effective_db_path)
    anomaly_retention_days = _int_env(
        "STORY_GEN_ANOMALY_RETENTION_DAYS",
        30,
        minimum=1,
        maximum=3650,
    )
    anomaly_max_rows = _int_env(
        "STORY_GEN_ANOMALY_MAX_ROWS",
        10_000,
        minimum=100,
        maximum=2_000_000,
    )
    bearer = HTTPBearer(auto_error=False)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        removed = anomaly_store.prune_anomalies(
            retention_days=anomaly_retention_days,
            max_rows=anomaly_max_rows,
        )
        logger.info("anomaly.prune removed=%s", removed)
        yield

    app = FastAPI(
        title="story_gen API",
        version="0.3.0",
        description=(
            "Local preview API for story blueprint editing and persistence. "
            "Designed for local/dev runtimes and future backend hosting."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        openapi_tags=[
            {"name": "system", "description": "Service health and runtime metadata."},
            {"name": "api", "description": "API discovery and root-level capability listing."},
            {"name": "auth", "description": "Registration, login, and profile lookups."},
            {"name": "stories", "description": "Story workspace CRUD and ownership-scoped reads."},
            {"name": "features", "description": "Story feature extraction workflows."},
            {
                "name": "analysis",
                "description": "Story intelligence extraction, translation, and scoring workflows.",
            },
            {"name": "dashboard", "description": "Visualization-oriented dashboard read models."},
            {
                "name": "essays",
                "description": "Essay workspace CRUD and deterministic quality checks.",
            },
        ],
        swagger_ui_parameters={
            "displayRequestDuration": True,
            "defaultModelsExpandDepth": -1,
        },
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    logger.info(
        "api.start db_path=%s anomaly_retention_days=%s anomaly_max_rows=%s",
        effective_db_path,
        anomaly_retention_days,
        anomaly_max_rows,
    )

    def record_anomaly(
        *,
        scope: str,
        code: str,
        severity: str,
        message: str,
        metadata: dict[str, object] | None = None,
    ) -> None:
        """Persist anomaly breadcrumbs and mirror concise warning logs."""
        anomaly = anomaly_store.write_anomaly(
            scope=scope,
            code=code,
            severity=severity,
            message=message,
            metadata=metadata,
        )
        logger.warning(
            "anomaly.recorded id=%s scope=%s code=%s severity=%s message=%s",
            anomaly.anomaly_id,
            scope,
            code,
            severity,
            message,
        )

    def owned_story_or_404(*, story_id: str, user: StoredUser) -> StoredStory:
        story = store.get_story(story_id=story_id)
        if story is None or story.owner_id != user.user_id:
            raise HTTPException(status_code=404, detail="Story not found")
        return story

    def latest_analysis_or_404(
        *,
        story: StoredStory,
        user: StoredUser,
    ) -> tuple[StoredAnalysisRun, StoryDocument, dict[str, object], str]:
        latest = analysis_store.get_latest_analysis(owner_id=user.user_id, story_id=story.story_id)
        if latest is None:
            raise HTTPException(status_code=404, detail="Analysis run not found")
        return latest

    def require_dashboard_dict(
        *,
        dashboard: dict[str, object],
        key: str,
        story_id: str,
        expected: str,
    ) -> dict[str, object]:
        payload = dashboard.get(key)
        if isinstance(payload, dict):
            return payload
        record_anomaly(
            scope="dashboard",
            code="invalid_payload_shape",
            severity="error",
            message=f"Expected {expected} for dashboard payload.",
            metadata={
                "story_id": story_id,
                "dashboard_key": key,
                "expected": expected,
                "actual_type": type(payload).__name__,
            },
        )
        raise HTTPException(status_code=500, detail=f"Invalid dashboard {key} payload")

    def require_dashboard_list(
        *,
        dashboard: dict[str, object],
        key: str,
        story_id: str,
        expected: str,
    ) -> list[object]:
        payload = dashboard.get(key)
        if isinstance(payload, list):
            return payload
        record_anomaly(
            scope="dashboard",
            code="invalid_payload_shape",
            severity="error",
            message=f"Expected {expected} for dashboard payload.",
            metadata={
                "story_id": story_id,
                "dashboard_key": key,
                "expected": expected,
                "actual_type": type(payload).__name__,
            },
        )
        raise HTTPException(status_code=500, detail=f"Invalid dashboard {key} payload")

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
        story = owned_story_or_404(story_id=story_id, user=user)
        return _story_response(story)

    @app.put("/api/v1/stories/{story_id}", response_model=StoryResponse, tags=["stories"])
    def update_story(
        story_id: str,
        payload: StoryUpdateRequest,
        user: StoredUser = Depends(current_user),
    ) -> StoryResponse:
        owned_story_or_404(story_id=story_id, user=user)
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
        story = owned_story_or_404(story_id=story_id, user=user)
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
        story = owned_story_or_404(story_id=story_id, user=user)
        latest = feature_store.get_latest_feature_result(
            owner_id=user.user_id, story_id=story.story_id
        )
        if latest is None:
            raise HTTPException(status_code=404, detail="Feature run not found")
        run, result = latest
        return _feature_run_response(run=run, result=result)

    @app.post(
        "/api/v1/stories/{story_id}/analysis/run",
        response_model=StoryAnalysisRunResponse,
        tags=["stories", "analysis"],
    )
    def run_analysis(
        story_id: str,
        payload: StoryAnalysisRunRequest,
        user: StoredUser = Depends(current_user),
    ) -> StoryAnalysisRunResponse:
        story = owned_story_or_404(story_id=story_id, user=user)
        blueprint = StoryBlueprint.model_validate_json(story.blueprint_json)
        source_text = (
            payload.source_text.strip() if payload.source_text else _analysis_source_text(blueprint)
        )
        if not source_text:
            raise HTTPException(
                status_code=422,
                detail="Story must include source text or chapter content to run analysis.",
            )
        analysis_result = run_story_analysis(
            story_id=story.story_id,
            source_text=source_text,
            source_type=payload.source_type,
            target_language=payload.target_language,
        )
        if not analysis_result.document.quality_gate.passed:
            record_anomaly(
                scope="analysis",
                code="quality_gate_failed",
                severity="warning",
                message="Story analysis run did not pass quality gate.",
                metadata={
                    "story_id": story.story_id,
                    "owner_id": user.user_id,
                    "reasons": analysis_result.document.quality_gate.reasons,
                    "confidence_floor": analysis_result.document.quality_gate.confidence_floor,
                    "hallucination_risk": analysis_result.document.quality_gate.hallucination_risk,
                    "translation_quality": analysis_result.document.quality_gate.translation_quality,
                },
            )
        run = analysis_store.write_analysis_result(owner_id=user.user_id, result=analysis_result)
        return _analysis_summary_response(run=run, document=analysis_result.document)

    @app.get(
        "/api/v1/stories/{story_id}/analysis/latest",
        response_model=StoryAnalysisRunResponse,
        tags=["stories", "analysis"],
    )
    def get_latest_analysis(
        story_id: str,
        user: StoredUser = Depends(current_user),
    ) -> StoryAnalysisRunResponse:
        story = owned_story_or_404(story_id=story_id, user=user)
        latest = latest_analysis_or_404(story=story, user=user)
        run, document, _, _ = latest
        return _analysis_summary_response(run=run, document=document)

    @app.get(
        "/api/v1/stories/{story_id}/dashboard/v1/overview",
        response_model=DashboardOverviewResponse,
        tags=["stories", "dashboard"],
    )
    @app.get(
        "/api/v1/stories/{story_id}/dashboard/overview",
        response_model=DashboardOverviewResponse,
        tags=["stories", "dashboard"],
    )
    def dashboard_overview(
        story_id: str,
        user: StoredUser = Depends(current_user),
    ) -> DashboardOverviewResponse:
        story = owned_story_or_404(story_id=story_id, user=user)
        latest = latest_analysis_or_404(story=story, user=user)
        _, _, dashboard, _ = latest
        payload = require_dashboard_dict(
            dashboard=dashboard,
            key="overview",
            story_id=story.story_id,
            expected="object",
        )
        return DashboardOverviewResponse.model_validate(payload)

    @app.get(
        "/api/v1/stories/{story_id}/dashboard/v1/timeline",
        response_model=list[DashboardTimelineLaneResponse],
        tags=["stories", "dashboard"],
    )
    @app.get(
        "/api/v1/stories/{story_id}/dashboard/timeline",
        response_model=list[DashboardTimelineLaneResponse],
        tags=["stories", "dashboard"],
    )
    def dashboard_timeline(
        story_id: str,
        user: StoredUser = Depends(current_user),
    ) -> list[DashboardTimelineLaneResponse]:
        story = owned_story_or_404(story_id=story_id, user=user)
        latest = latest_analysis_or_404(story=story, user=user)
        _, _, dashboard, _ = latest
        payload = require_dashboard_list(
            dashboard=dashboard,
            key="timeline_lanes",
            story_id=story.story_id,
            expected="array",
        )
        return [DashboardTimelineLaneResponse.model_validate(item) for item in payload]

    @app.get(
        "/api/v1/stories/{story_id}/dashboard/v1/themes/heatmap",
        response_model=list[DashboardThemeHeatmapCellResponse],
        tags=["stories", "dashboard"],
    )
    @app.get(
        "/api/v1/stories/{story_id}/dashboard/themes/heatmap",
        response_model=list[DashboardThemeHeatmapCellResponse],
        tags=["stories", "dashboard"],
    )
    def dashboard_theme_heatmap(
        story_id: str,
        user: StoredUser = Depends(current_user),
    ) -> list[DashboardThemeHeatmapCellResponse]:
        story = owned_story_or_404(story_id=story_id, user=user)
        latest = latest_analysis_or_404(story=story, user=user)
        _, _, dashboard, _ = latest
        payload = require_dashboard_list(
            dashboard=dashboard,
            key="theme_heatmap",
            story_id=story.story_id,
            expected="array",
        )
        return [DashboardThemeHeatmapCellResponse.model_validate(item) for item in payload]

    @app.get(
        "/api/v1/stories/{story_id}/dashboard/arcs",
        response_model=list[DashboardArcPointResponse],
        tags=["stories", "dashboard"],
    )
    def dashboard_arcs(
        story_id: str,
        user: StoredUser = Depends(current_user),
    ) -> list[DashboardArcPointResponse]:
        story = owned_story_or_404(story_id=story_id, user=user)
        latest = latest_analysis_or_404(story=story, user=user)
        _, _, dashboard, _ = latest
        payload = require_dashboard_list(
            dashboard=dashboard,
            key="arc_points",
            story_id=story.story_id,
            expected="array",
        )
        return [DashboardArcPointResponse.model_validate(item) for item in payload]

    @app.get(
        "/api/v1/stories/{story_id}/dashboard/drilldown/{item_id}",
        response_model=DashboardDrilldownResponse,
        tags=["stories", "dashboard"],
    )
    def dashboard_drilldown(
        story_id: str,
        item_id: str,
        user: StoredUser = Depends(current_user),
    ) -> DashboardDrilldownResponse:
        story = owned_story_or_404(story_id=story_id, user=user)
        latest = latest_analysis_or_404(story=story, user=user)
        _, _, dashboard, _ = latest
        drilldown = require_dashboard_dict(
            dashboard=dashboard,
            key="drilldown",
            story_id=story.story_id,
            expected="object",
        )
        item = drilldown.get(item_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Dashboard item not found")
        if not isinstance(item, dict):
            record_anomaly(
                scope="dashboard",
                code="invalid_payload_shape",
                severity="error",
                message="Dashboard drilldown item is not an object.",
                metadata={
                    "story_id": story.story_id,
                    "dashboard_key": "drilldown",
                    "item_id": item_id,
                    "actual_type": type(item).__name__,
                },
            )
            raise HTTPException(status_code=500, detail="Invalid dashboard drilldown item")
        return DashboardDrilldownResponse.model_validate(item)

    @app.get(
        "/api/v1/stories/{story_id}/dashboard/graph",
        response_model=DashboardGraphResponse,
        tags=["stories", "dashboard"],
    )
    def dashboard_graph(
        story_id: str,
        user: StoredUser = Depends(current_user),
    ) -> DashboardGraphResponse:
        story = owned_story_or_404(story_id=story_id, user=user)
        latest = latest_analysis_or_404(story=story, user=user)
        _, _, dashboard, _ = latest
        node_payload = require_dashboard_list(
            dashboard=dashboard,
            key="graph_nodes",
            story_id=story.story_id,
            expected="array",
        )
        edge_payload = require_dashboard_list(
            dashboard=dashboard,
            key="graph_edges",
            story_id=story.story_id,
            expected="array",
        )
        nodes = [DashboardGraphNodeResponse.model_validate(item) for item in node_payload]
        edges = [DashboardGraphEdgeResponse.model_validate(item) for item in edge_payload]
        return DashboardGraphResponse(nodes=nodes, edges=edges)

    @app.get(
        "/api/v1/stories/{story_id}/dashboard/graph/export.svg",
        response_model=DashboardGraphExportResponse,
        tags=["stories", "dashboard"],
    )
    def dashboard_graph_export_svg(
        story_id: str,
        user: StoredUser = Depends(current_user),
    ) -> DashboardGraphExportResponse:
        story = owned_story_or_404(story_id=story_id, user=user)
        latest = latest_analysis_or_404(story=story, user=user)
        _, _, _, graph_svg = latest
        return DashboardGraphExportResponse(svg=graph_svg)

    @app.get(
        "/api/v1/stories/{story_id}/dashboard/graph/export.png",
        response_model=DashboardGraphPngExportResponse,
        tags=["stories", "dashboard"],
    )
    def dashboard_graph_export_png(
        story_id: str,
        user: StoredUser = Depends(current_user),
    ) -> DashboardGraphPngExportResponse:
        story = owned_story_or_404(story_id=story_id, user=user)
        latest = latest_analysis_or_404(story=story, user=user)
        _, _, dashboard, _ = latest
        node_payload = require_dashboard_list(
            dashboard=dashboard,
            key="graph_nodes",
            story_id=story.story_id,
            expected="array",
        )
        edge_payload = require_dashboard_list(
            dashboard=dashboard,
            key="graph_edges",
            story_id=story.story_id,
            expected="array",
        )
        nodes = [DashboardGraphNodeResponse.model_validate(item) for item in node_payload]
        edges = [DashboardGraphEdgeResponse.model_validate(item) for item in edge_payload]
        png_bytes = export_graph_png(
            nodes=[
                GraphNode(
                    id=node.id,
                    label=node.label,
                    group=node.group,
                    stage=cast(StoryStage | None, node.stage),
                    layout_x=node.layout_x,
                    layout_y=node.layout_y,
                )
                for node in nodes
            ],
            edges=[
                GraphEdge(
                    source=edge.source,
                    target=edge.target,
                    relation=edge.relation,
                    weight=edge.weight,
                )
                for edge in edges
            ],
        )
        return DashboardGraphPngExportResponse(
            png_base64=base64.b64encode(png_bytes).decode("ascii")
        )

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
