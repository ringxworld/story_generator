"""Deterministic event and entity extraction from translated segments."""

from __future__ import annotations

import re
from collections import defaultdict

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
_SENTENCE_SPLIT = re.compile(r"[.!?]+\s+")


def extract_events_and_entities(
    *,
    segments: list[RawSegment],
) -> tuple[list[ExtractedEvent], list[EntityMention]]:
    """Extract event and entity artifacts from normalized story segments."""
    # TODO(#1005): Replace regex extractor with model-backed event/entity extraction.
    validate_extraction_input(segments)
    events: list[ExtractedEvent] = []
    entities_by_name: dict[str, list[str]] = defaultdict(list)

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
                confidence=ConfidenceScore(method="extract.rule.v1", score=0.72),
                provenance=ProvenanceRecord(
                    source_segment_ids=[segment.segment_id],
                    generator="event_extractor",
                ),
            )
        )

    validate_extraction_output(events)
    entities = _build_entities(entities_by_name)
    return events, entities


def _build_entities(mentions: dict[str, list[str]]) -> list[EntityMention]:
    entities: list[EntityMention] = []
    for name in sorted(mentions):
        segment_ids = sorted(set(mentions[name]))
        entities.append(
            EntityMention(
                entity_id=stable_id(prefix="ent", text=name),
                name=name,
                entity_type="character",
                mention_count=len(mentions[name]),
                segment_ids=segment_ids,
                confidence=ConfidenceScore(method="extract.rule.v1", score=0.68),
                provenance=ProvenanceRecord(
                    source_segment_ids=segment_ids,
                    generator="entity_extractor",
                ),
            )
        )
    return entities
