"""Narrative segmentation and beat detection."""

from __future__ import annotations

from typing import Literal

from story_gen.core.pipeline_contracts import validate_beat_input, validate_beat_output
from story_gen.core.story_schema import (
    ConfidenceScore,
    ExtractedEvent,
    ProvenanceRecord,
    StoryBeat,
    stable_id,
)

StageName = Literal["setup", "escalation", "climax", "resolution"]
_STAGES: tuple[StageName, StageName, StageName, StageName] = (
    "setup",
    "escalation",
    "climax",
    "resolution",
)


def detect_story_beats(*, events: list[ExtractedEvent]) -> list[StoryBeat]:
    """Map extracted events to deterministic stage beats."""
    validate_beat_input(events)
    total = len(events)
    beats: list[StoryBeat] = []
    for index, event in enumerate(events, start=1):
        stage = _stage_for_position(position=index, total=total)
        beats.append(
            StoryBeat(
                beat_id=stable_id(prefix="beat", text=f"{event.event_id}:{stage}"),
                stage=stage,
                order_index=index,
                summary=event.summary,
                timestamp_utc=event.event_time_utc,
                evidence_segment_ids=[event.segment_id],
                confidence=ConfidenceScore(method="beat.rule.v1", score=0.71),
                provenance=ProvenanceRecord(
                    source_segment_ids=[event.segment_id],
                    generator="beat_detector",
                ),
            )
        )
    validate_beat_output(beats)
    return beats


def _stage_for_position(*, position: int, total: int) -> StageName:
    if total <= 3:
        if position == 1:
            return "setup"
        if position == total:
            return "resolution"
        return "climax"
    quarter = max(1, total // 4)
    if position <= quarter:
        return _STAGES[0]
    if position <= quarter * 2:
        return _STAGES[1]
    if position <= quarter * 3:
        return _STAGES[2]
    return _STAGES[3]
