"""Narrative segmentation and beat detection."""

from __future__ import annotations

import re
from typing import Final

from story_gen.core.pipeline_contracts import validate_beat_input, validate_beat_output
from story_gen.core.story_schema import (
    STORY_STAGE_ORDER,
    ConfidenceScore,
    ExtractedEvent,
    ProvenanceRecord,
    StoryBeat,
    StoryStage,
    stable_id,
)

_WORD_TOKEN = re.compile(r"[A-Za-z']+")
_STAGE_CUES: Final[dict[StoryStage, set[str]]] = {
    "setup": {
        "arrives",
        "begins",
        "discovers",
        "enters",
        "finds",
        "opens",
        "starts",
    },
    "escalation": {
        "accuses",
        "conflict",
        "denies",
        "doubt",
        "pressures",
        "tension",
        "threat",
    },
    "climax": {
        "breaks",
        "confronts",
        "decides",
        "exposes",
        "fight",
        "reveals",
        "turning",
    },
    "resolution": {
        "accepts",
        "closes",
        "heals",
        "peace",
        "reconciles",
        "resolves",
        "restores",
    },
}


def detect_story_beats(*, events: list[ExtractedEvent]) -> list[StoryBeat]:
    """Map extracted events to deterministic, cue-aware stage beats."""
    validate_beat_input(events)
    total = len(events)
    beats: list[StoryBeat] = []
    previous_stage_index = 0
    for index, event in enumerate(events, start=1):
        stage, stage_score = _stage_for_event(
            event=event,
            position=index,
            total=total,
            previous_stage_index=previous_stage_index,
        )
        previous_stage_index = STORY_STAGE_ORDER.index(stage)
        confidence = round(min(0.95, 0.64 + (stage_score * 0.24)), 3)
        beats.append(
            StoryBeat(
                beat_id=stable_id(prefix="beat", text=f"{event.event_id}:{stage}"),
                stage=stage,
                order_index=index,
                summary=event.summary,
                timestamp_utc=event.event_time_utc,
                evidence_segment_ids=[event.segment_id],
                confidence=ConfidenceScore(method="beat.hybrid.v2", score=confidence),
                provenance=ProvenanceRecord(
                    source_segment_ids=[event.segment_id],
                    generator="beat_detector_hybrid",
                ),
            )
        )
    validate_beat_output(beats)
    return beats


def _stage_for_position(*, position: int, total: int) -> StoryStage:
    if total <= 3:
        if position == 1:
            return "setup"
        if position == total:
            return "resolution"
        return "climax"
    quarter = max(1, total // 4)
    if position <= quarter:
        return STORY_STAGE_ORDER[0]
    if position <= quarter * 2:
        return STORY_STAGE_ORDER[1]
    if position <= quarter * 3:
        return STORY_STAGE_ORDER[2]
    return STORY_STAGE_ORDER[3]


def _stage_for_event(
    *,
    event: ExtractedEvent,
    position: int,
    total: int,
    previous_stage_index: int,
) -> tuple[StoryStage, float]:
    expected = _stage_for_position(position=position, total=total)
    expected_index = STORY_STAGE_ORDER.index(expected)
    tokens = [token.lower() for token in _WORD_TOKEN.findall(event.summary)]
    token_count = max(1, len(tokens))
    lexical_scores: dict[StoryStage, float] = {}
    for stage in STORY_STAGE_ORDER:
        hits = sum(1 for token in tokens if token in _STAGE_CUES[stage])
        lexical_scores[stage] = hits / token_count
    blended: dict[StoryStage, float] = {}
    for stage in STORY_STAGE_ORDER:
        stage_index = STORY_STAGE_ORDER.index(stage)
        positional = max(0.0, 1.0 - (abs(stage_index - expected_index) * 0.45))
        blended[stage] = (lexical_scores[stage] * 0.72) + (positional * 0.28)
    ranked = sorted(blended.items(), key=lambda pair: (-pair[1], pair[0]))
    selected_stage, selected_score = ranked[0]
    selected_index = STORY_STAGE_ORDER.index(selected_stage)
    max_allowed = min(len(STORY_STAGE_ORDER) - 1, previous_stage_index + 2)
    clamped_index = max(previous_stage_index, min(selected_index, max_allowed))
    clamped_stage = STORY_STAGE_ORDER[clamped_index]
    return clamped_stage, blended[clamped_stage]
