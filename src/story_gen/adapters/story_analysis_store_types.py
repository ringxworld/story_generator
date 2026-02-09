"""Shared types for story analysis persistence adapters."""

from __future__ import annotations

from dataclasses import dataclass

from story_gen.core.story_schema import StoryDocument


@dataclass(frozen=True)
class StoredAnalysisRun:
    """Persisted analysis run metadata."""

    run_id: str
    story_id: str
    owner_id: str
    schema_version: str
    analyzed_at_utc: str


LatestAnalysisPayload = tuple[StoredAnalysisRun, StoryDocument, dict[str, object], str]
