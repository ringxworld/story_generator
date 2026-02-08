"""Temporal model and timeline composition utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from story_gen.core.pipeline_contracts import validate_timeline_input, validate_timeline_output
from story_gen.core.story_schema import (
    ConfidenceScore,
    ExtractedEvent,
    ProvenanceRecord,
    StoryBeat,
    TimelinePoint,
    stable_id,
)

StageName = Literal["setup", "escalation", "climax", "resolution"]


@dataclass(frozen=True)
class ComposedTimeline:
    """Timeline output with dual chronology views."""

    actual_time: list[TimelinePoint]
    narrative_order: list[TimelinePoint]


def compose_timeline(
    *,
    events: list[ExtractedEvent],
    beats: list[StoryBeat],
) -> ComposedTimeline:
    """Build actual-time and narrative-order timelines from events and beats."""
    validate_timeline_input(events, beats)
    points: list[TimelinePoint] = []
    for event in events:
        points.append(
            TimelinePoint(
                point_id=stable_id(prefix="tl", text=f"event:{event.event_id}"),
                source_id=event.event_id,
                source_type="event",
                label=event.summary,
                narrative_order=event.narrative_order,
                actual_time_utc=event.event_time_utc,
                stage=_stage_for_order(event.narrative_order, len(events)),
                confidence=ConfidenceScore(method="timeline.rule.v1", score=0.74),
                provenance=ProvenanceRecord(
                    source_segment_ids=[event.segment_id],
                    generator="timeline_composer",
                ),
            )
        )
    for beat in beats:
        points.append(
            TimelinePoint(
                point_id=stable_id(prefix="tl", text=f"beat:{beat.beat_id}"),
                source_id=beat.beat_id,
                source_type="beat",
                label=beat.summary,
                narrative_order=beat.order_index,
                actual_time_utc=beat.timestamp_utc,
                stage=beat.stage,
                confidence=ConfidenceScore(method="timeline.rule.v1", score=0.76),
                provenance=ProvenanceRecord(
                    source_segment_ids=beat.evidence_segment_ids,
                    generator="timeline_composer",
                ),
            )
        )

    narrative_order = sorted(
        points,
        key=lambda point: (point.narrative_order, point.source_type, point.source_id),
    )
    actual_time = sorted(
        points,
        key=lambda point: (
            point.actual_time_utc is None,
            point.actual_time_utc or "",
            point.narrative_order,
            point.source_id,
        ),
    )
    for index, point in enumerate(narrative_order, start=1):
        narrative_order[index - 1] = point.model_copy(update={"narrative_order": index})
    validate_timeline_output(narrative_order)
    return ComposedTimeline(actual_time=actual_time, narrative_order=narrative_order)


def _stage_for_order(order: int, total: int) -> StageName:
    if total <= 1:
        return "setup"
    ratio = order / total
    if ratio <= 0.25:
        return "setup"
    if ratio <= 0.5:
        return "escalation"
    if ratio <= 0.75:
        return "climax"
    return "resolution"
