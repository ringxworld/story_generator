"""Canonical story analysis schema shared across intelligence pipeline stages."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from hashlib import sha256
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

STORY_SCHEMA_VERSION: Final[Literal["story_analysis.v1"]] = "story_analysis.v1"
_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{1,119}$")


def utc_now_iso() -> str:
    """Return current UTC timestamp in ISO-8601 form."""
    return datetime.now(UTC).isoformat()


def stable_id(*, prefix: str, text: str, length: int = 12) -> str:
    """Build deterministic identifier from normalized text payload."""
    digest = sha256(text.encode("utf-8")).hexdigest()[:length]
    return f"{prefix}_{digest}"


class SchemaModel(BaseModel):
    """Strict model configuration for pipeline artifacts."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ConfidenceScore(SchemaModel):
    """Confidence metadata attached to derived artifacts."""

    method: str = Field(min_length=1, max_length=120)
    score: float = Field(ge=0.0, le=1.0)


class ProvenanceRecord(SchemaModel):
    """Provenance metadata for generated records."""

    source_segment_ids: list[str] = Field(default_factory=list)
    created_at_utc: str = Field(default_factory=utc_now_iso)
    generator: str = Field(min_length=1, max_length=120)
    generator_version: str = Field(min_length=1, max_length=60, default="v1")

    @field_validator("source_segment_ids")
    @classmethod
    def _dedupe_segments(cls, values: list[str]) -> list[str]:
        seen: set[str] = set()
        deduped: list[str] = []
        for value in values:
            item = value.strip().lower()
            if not item or item in seen:
                continue
            seen.add(item)
            deduped.append(item)
        return deduped


class RawSegment(SchemaModel):
    """One normalized chunk from raw source text."""

    segment_id: str = Field(min_length=3, max_length=140)
    source_type: Literal["text", "document", "transcript"] = "text"
    original_text: str = Field(min_length=1)
    normalized_text: str = Field(min_length=1)
    language_code: str = Field(min_length=2, max_length=16, default="und")
    translated_text: str | None = None
    segment_index: int = Field(ge=1)
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=1)

    @field_validator("segment_id")
    @classmethod
    def _validate_segment_id(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not _ID_PATTERN.match(normalized):
            raise ValueError("segment_id must match lowercase id pattern.")
        return normalized


class ExtractedEvent(SchemaModel):
    """Atomic event extracted from one or more segments."""

    event_id: str = Field(min_length=3, max_length=140)
    summary: str = Field(min_length=1, max_length=4000)
    segment_id: str = Field(min_length=3, max_length=140)
    narrative_order: int = Field(ge=1)
    event_time_utc: str | None = None
    entity_names: list[str] = Field(default_factory=list)
    confidence: ConfidenceScore
    provenance: ProvenanceRecord


class StoryBeat(SchemaModel):
    """Narrative beat mapped to a story stage."""

    beat_id: str = Field(min_length=3, max_length=140)
    stage: Literal["setup", "escalation", "climax", "resolution"]
    order_index: int = Field(ge=1)
    summary: str = Field(min_length=1, max_length=4000)
    timestamp_utc: str | None = None
    evidence_segment_ids: list[str] = Field(min_length=1)
    confidence: ConfidenceScore
    provenance: ProvenanceRecord


class ThemeSignal(SchemaModel):
    """Theme evolution signal at beat/stage level."""

    theme_id: str = Field(min_length=3, max_length=140)
    label: str = Field(min_length=1, max_length=200)
    stage: Literal["setup", "escalation", "climax", "resolution"]
    strength: float = Field(ge=0.0, le=1.0)
    direction: Literal["emerging", "strengthening", "steady", "fading"]
    evidence_segment_ids: list[str] = Field(min_length=1)
    confidence: ConfidenceScore
    provenance: ProvenanceRecord


class EntityMention(SchemaModel):
    """Entity mention tracked across segments."""

    entity_id: str = Field(min_length=3, max_length=140)
    name: str = Field(min_length=1, max_length=200)
    entity_type: Literal["character", "location", "organization", "concept"] = "character"
    mention_count: int = Field(ge=1)
    segment_ids: list[str] = Field(min_length=1)
    confidence: ConfidenceScore
    provenance: ProvenanceRecord


class TimelinePoint(SchemaModel):
    """Timeline item used by both chronology and narrative-order views."""

    point_id: str = Field(min_length=3, max_length=140)
    source_id: str = Field(min_length=3, max_length=140)
    source_type: Literal["event", "beat"]
    label: str = Field(min_length=1, max_length=1000)
    narrative_order: int = Field(ge=1)
    actual_time_utc: str | None = None
    stage: Literal["setup", "escalation", "climax", "resolution"]
    confidence: ConfidenceScore
    provenance: ProvenanceRecord


class Insight(SchemaModel):
    """Insight generated at macro/meso/micro granularity."""

    insight_id: str = Field(min_length=3, max_length=140)
    granularity: Literal["macro", "meso", "micro"]
    title: str = Field(min_length=1, max_length=240)
    content: str = Field(min_length=1, max_length=8000)
    stage: Literal["setup", "escalation", "climax", "resolution"] | None = None
    beat_id: str | None = None
    evidence_segment_ids: list[str] = Field(min_length=1)
    confidence: ConfidenceScore
    provenance: ProvenanceRecord


class QualityGate(SchemaModel):
    """Evaluation status used before dashboard exposure."""

    passed: bool
    confidence_floor: float = Field(ge=0.0, le=1.0)
    hallucination_risk: float = Field(ge=0.0, le=1.0)
    translation_quality: float = Field(ge=0.0, le=1.0)
    reasons: list[str] = Field(default_factory=list)


class StoryDocument(SchemaModel):
    """Canonical end-to-end story intelligence artifact."""

    schema_version: Literal["story_analysis.v1"] = STORY_SCHEMA_VERSION
    story_id: str = Field(min_length=1)
    source_language: str = Field(min_length=2, max_length=16)
    target_language: str = Field(min_length=2, max_length=16, default="en")
    raw_segments: list[RawSegment] = Field(min_length=1)
    extracted_events: list[ExtractedEvent] = Field(default_factory=list)
    story_beats: list[StoryBeat] = Field(default_factory=list)
    theme_signals: list[ThemeSignal] = Field(default_factory=list)
    entity_mentions: list[EntityMention] = Field(default_factory=list)
    timeline_points: list[TimelinePoint] = Field(default_factory=list)
    insights: list[Insight] = Field(default_factory=list)
    quality_gate: QualityGate

