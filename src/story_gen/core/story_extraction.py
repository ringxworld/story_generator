"""Model-assisted event/entity extraction with deterministic fallback."""

from __future__ import annotations

import os
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from story_gen.core.pipeline_contracts import validate_extraction_input, validate_extraction_output
from story_gen.core.story_schema import (
    ConfidenceScore,
    EntityMention,
    ExtractedEvent,
    ProvenanceRecord,
    RawSegment,
    stable_id,
)

_ENTITY_TOKEN = re.compile(r"\b[A-Z][a-z]{2,}\b")
_WORD_TOKEN = re.compile(r"[A-Za-z']+")
_SENTENCE_SPLIT = re.compile(r"[.!?]+\s+")
_ISO_DATE = re.compile(
    r"\b(?P<date>\d{4}-\d{2}-\d{2})(?:[ T](?P<time>\d{2}:\d{2}(?::\d{2})?)Z?)?\b"
)
_EVENT_CUES: dict[str, float] = {
    "finds": 0.8,
    "discovers": 0.85,
    "denies": 0.9,
    "confronts": 0.95,
    "reveals": 0.9,
    "accepts": 0.85,
    "heals": 0.8,
    "conflict": 0.75,
}
_ENTITY_SEED_TERMS = {"rhea", "council", "city", "archive", "ledger", "family"}


@dataclass(frozen=True)
class ExtractionIssue:
    code: str
    severity: Literal["warning", "error"]
    message: str


@dataclass(frozen=True)
class ExtractionDiagnostics:
    provider: str
    fallback_used: bool
    issue_count: int
    issues: list[ExtractionIssue]


def extract_events_and_entities(
    *,
    segments: list[RawSegment],
) -> tuple[list[ExtractedEvent], list[EntityMention]]:
    """Extract event and entity artifacts from translated segments."""
    events, entities, _ = extract_events_and_entities_with_diagnostics(segments=segments)
    return events, entities


def extract_events_and_entities_with_diagnostics(
    *,
    segments: list[RawSegment],
) -> tuple[list[ExtractedEvent], list[EntityMention], ExtractionDiagnostics]:
    """Extract with configurable provider and deterministic fallback."""
    validate_extraction_input(segments)
    provider = os.environ.get("STORY_GEN_EXTRACTION_PROVIDER", "cue_model.v1").strip().lower()
    issues: list[ExtractionIssue] = []
    fallback_used = False
    downgrade_confidence = False
    selected_provider = "cue_model.v1"

    if provider in {"", "cue_model.v1", "cue-model"}:
        try:
            events, entities = _extract_cue_model(segments=segments)
            validate_extraction_output(events)
            return (
                events,
                entities,
                ExtractionDiagnostics(
                    provider="cue_model.v1",
                    fallback_used=False,
                    issue_count=0,
                    issues=[],
                ),
            )
        except Exception as exc:  # noqa: BLE001
            fallback_used = True
            downgrade_confidence = True
            issues.append(
                ExtractionIssue(
                    code="extraction_provider_failed",
                    severity="warning",
                    message=f"cue_model.v1 failed: {exc}",
                )
            )
            selected_provider = "rule_fallback.v1"
    elif provider in {"rule.v1", "rule"}:
        selected_provider = "rule.v1"
    else:
        fallback_used = True
        downgrade_confidence = True
        selected_provider = "rule_fallback.v1"
        issues.append(
            ExtractionIssue(
                code="extraction_provider_unrecognized",
                severity="warning",
                message=f"Unknown extraction provider '{provider}', using deterministic fallback.",
            )
        )

    events, entities = _extract_rule_fallback(
        segments=segments,
        downgrade_confidence=downgrade_confidence,
    )
    if fallback_used:
        issues.append(
            ExtractionIssue(
                code="extraction_fallback_used",
                severity="warning",
                message="Rule fallback extractor was used with downgraded confidence.",
            )
        )
    validate_extraction_output(events)
    return (
        events,
        entities,
        ExtractionDiagnostics(
            provider=selected_provider,
            fallback_used=fallback_used,
            issue_count=len(issues),
            issues=issues,
        ),
    )


def _extract_cue_model(
    *, segments: list[RawSegment]
) -> tuple[list[ExtractedEvent], list[EntityMention]]:
    if os.environ.get("STORY_GEN_EXTRACTION_FORCE_FAIL", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }:
        raise RuntimeError("Forced extraction failure was configured.")

    events: list[ExtractedEvent] = []
    entities_by_name: dict[str, list[str]] = defaultdict(list)
    for order, segment in enumerate(segments, start=1):
        source_text = (segment.translated_text or segment.normalized_text).strip()
        if "[FAIL_EXTRACT]" in source_text:
            raise RuntimeError("Source text contains [FAIL_EXTRACT] marker.")
        summary = _event_summary_from_text(source_text)[:4000]
        entity_names = _entity_names_for_segment(segment, source_text)
        for entity in entity_names:
            entities_by_name[entity].append(segment.segment_id)
        cue_strength = _cue_strength(summary)
        confidence = _bounded(0.62 + (cue_strength * 0.2) + (len(entity_names) * 0.025))
        events.append(
            ExtractedEvent(
                event_id=stable_id(prefix="evt", text=f"{segment.segment_id}:{summary}"),
                summary=summary,
                segment_id=segment.segment_id,
                narrative_order=order,
                event_time_utc=_event_time_from_text(source_text),
                entity_names=entity_names,
                confidence=ConfidenceScore(method="extract.cue_model.v1", score=confidence),
                provenance=ProvenanceRecord(
                    source_segment_ids=[segment.segment_id],
                    generator="event_extractor_cue_model",
                ),
            )
        )
    entities = _build_entities(
        mentions=entities_by_name,
        method="extract.cue_model.v1",
        base_confidence=0.71,
    )
    return events, entities


def _extract_rule_fallback(
    *, segments: list[RawSegment], downgrade_confidence: bool
) -> tuple[list[ExtractedEvent], list[EntityMention]]:
    events: list[ExtractedEvent] = []
    entities_by_name: dict[str, list[str]] = defaultdict(list)
    event_confidence = 0.52 if downgrade_confidence else 0.72
    entity_confidence = 0.48 if downgrade_confidence else 0.68
    method = "extract.fallback.v1" if downgrade_confidence else "extract.rule.v1"
    for order, segment in enumerate(segments, start=1):
        source_text = segment.translated_text or segment.normalized_text
        sentences = [chunk.strip() for chunk in _SENTENCE_SPLIT.split(source_text) if chunk.strip()]
        if not sentences:
            sentences = [source_text]
        event_summary = sentences[0][:4000]
        entity_names = sorted(
            {token.lower() for token in _ENTITY_TOKEN.findall(segment.original_text)}
        )
        for entity in entity_names:
            entities_by_name[entity].append(segment.segment_id)
        events.append(
            ExtractedEvent(
                event_id=stable_id(prefix="evt", text=f"{segment.segment_id}:{event_summary}"),
                summary=event_summary,
                segment_id=segment.segment_id,
                narrative_order=order,
                event_time_utc=None,
                entity_names=entity_names,
                confidence=ConfidenceScore(method=method, score=event_confidence),
                provenance=ProvenanceRecord(
                    source_segment_ids=[segment.segment_id],
                    generator="event_extractor_fallback"
                    if downgrade_confidence
                    else "event_extractor",
                ),
            )
        )
    entities = _build_entities(
        mentions=entities_by_name, method=method, base_confidence=entity_confidence
    )
    return events, entities


def _event_summary_from_text(text: str) -> str:
    sentences = [chunk.strip() for chunk in _SENTENCE_SPLIT.split(text) if chunk.strip()]
    if not sentences:
        return text
    ranked = sorted(
        sentences, key=lambda sentence: (_cue_strength(sentence), len(sentence)), reverse=True
    )
    return ranked[0]


def _entity_names_for_segment(segment: RawSegment, source_text: str) -> list[str]:
    names = {token.lower() for token in _ENTITY_TOKEN.findall(segment.original_text)}
    source_tokens = {token.lower() for token in _WORD_TOKEN.findall(source_text)}
    for token in source_tokens:
        if token in _ENTITY_SEED_TERMS:
            names.add(token)
    return sorted(names)


def _build_entities(
    *,
    mentions: dict[str, list[str]],
    method: str,
    base_confidence: float,
) -> list[EntityMention]:
    entities: list[EntityMention] = []
    for name in sorted(mentions):
        segment_ids = sorted(set(mentions[name]))
        confidence = _bounded(base_confidence + min(0.18, len(segment_ids) * 0.04))
        entities.append(
            EntityMention(
                entity_id=stable_id(prefix="ent", text=name),
                name=name,
                entity_type="character",
                mention_count=len(mentions[name]),
                segment_ids=segment_ids,
                confidence=ConfidenceScore(method=method, score=confidence),
                provenance=ProvenanceRecord(
                    source_segment_ids=segment_ids,
                    generator="entity_extractor_cue_model"
                    if method.startswith("extract.cue_model")
                    else "entity_extractor_fallback",
                ),
            )
        )
    return entities


def _event_time_from_text(text: str) -> str | None:
    match = _ISO_DATE.search(text)
    if not match:
        return None
    date_part = match.group("date")
    time_part = match.group("time") or "00:00:00"
    if len(time_part) == 5:
        time_part = f"{time_part}:00"
    value = f"{date_part}T{time_part}+00:00"
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat()


def _cue_strength(text: str) -> float:
    tokens = [token.lower() for token in _WORD_TOKEN.findall(text)]
    if not tokens:
        return 0.0
    score = 0.0
    for token in tokens:
        score += _EVENT_CUES.get(token, 0.0)
    return min(1.0, score / max(1, len(tokens)))


def _bounded(value: float) -> float:
    return round(min(0.98, max(0.0, value)), 3)
