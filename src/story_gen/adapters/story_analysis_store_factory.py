"""Factory and protocol for selecting story analysis persistence adapters."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol

from story_gen.adapters.graph_story_analysis_store import GraphStoryAnalysisStore
from story_gen.adapters.mongo_story_analysis_store import MongoStoryAnalysisStore
from story_gen.adapters.sqlite_story_analysis_store import SQLiteStoryAnalysisStore
from story_gen.adapters.story_analysis_store_types import LatestAnalysisPayload, StoredAnalysisRun
from story_gen.core.story_analysis_pipeline import StoryAnalysisResult


class StoryAnalysisStorePort(Protocol):
    """Persistence operations needed by API and CLI for analysis read/write."""

    def write_analysis_result(
        self,
        *,
        owner_id: str,
        result: StoryAnalysisResult,
    ) -> StoredAnalysisRun: ...

    def get_latest_analysis(
        self,
        *,
        owner_id: str,
        story_id: str,
    ) -> LatestAnalysisPayload | None: ...


def _env_flag(name: str) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def create_story_analysis_store(*, db_path: Path) -> StoryAnalysisStorePort:
    """Build configured analysis store backend with safe feature-flag gating."""
    backend = os.environ.get("STORY_GEN_ANALYSIS_BACKEND", "sqlite").strip().lower()
    if backend in {"", "sqlite"}:
        return SQLiteStoryAnalysisStore(db_path=db_path)
    if backend == "mongo-prototype":
        if not _env_flag("STORY_GEN_ENABLE_MONGO_ADAPTER"):
            raise RuntimeError(
                "STORY_GEN_ANALYSIS_BACKEND=mongo-prototype requires "
                "STORY_GEN_ENABLE_MONGO_ADAPTER=1."
            )
        return MongoStoryAnalysisStore(db_path=db_path)
    if backend == "graph-prototype":
        if not _env_flag("STORY_GEN_ENABLE_GRAPH_ADAPTER"):
            raise RuntimeError(
                "STORY_GEN_ANALYSIS_BACKEND=graph-prototype requires "
                "STORY_GEN_ENABLE_GRAPH_ADAPTER=1."
            )
        return GraphStoryAnalysisStore(db_path=db_path)
    raise RuntimeError(
        "Unsupported STORY_GEN_ANALYSIS_BACKEND value. "
        "Expected sqlite, mongo-prototype, or graph-prototype."
    )
