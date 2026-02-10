"""Temporal model and timeline composition utilities."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from story_gen.core.pipeline_contracts import validate_timeline_input, validate_timeline_output
from story_gen.core.story_schema import (
    ConfidenceScore,
    ExtractedEvent,
    ProvenanceRecord,
    StoryBeat,
    StoryStage,
    TimelinePoint,
    stable_id,
)

_ISO_DATE = re.compile(
    r"\b(?P<date>\d{4}-\d{2}-\d{2})(?:[ T](?P<time>\d{2}:\d{2}(?::\d{2})?)Z?)?\b"
)


@dataclass(frozen=True)
class TimelineConflict:
    """Deterministic timeline discrepancy diagnostic."""

    conflict_id: str
    code: str
    severity: str
    message: str
    source_ids: tuple[str, ...]


@dataclass(frozen=True)
class ComposedTimeline:
    """Timeline output with dual chronology views and diagnostics."""

    actual_time: list[TimelinePoint]
    narrative_order: list[TimelinePoint]
    conflicts: list[TimelineConflict]
    consistency_score: float


def compose_timeline(
    *,
    events: list[ExtractedEvent],
    beats: list[StoryBeat],
) -> ComposedTimeline:
    """Build actual-time and narrative-order timelines from events and beats."""
    validate_timeline_input(events, beats)
    points: list[TimelinePoint] = []
    beats_by_segment: dict[str, StoryBeat] = {}
    for beat in beats:
        for segment_id in beat.evidence_segment_ids:
            beats_by_segment[segment_id] = beat
    previous_known_time: str | None = None
    total_events = max(1, len(events))
    sorted_events = sorted(events, key=lambda event: (event.narrative_order, event.event_id))
    for event in sorted_events:
        linked_beat = _linked_beat_for_event(
            event=event, beats=beats, beats_by_segment=beats_by_segment
        )
        inferred_time, inferred_reason = _infer_event_time(
            event=event,
            linked_beat=linked_beat,
            previous_known_time=previous_known_time,
            narrative_order=event.narrative_order,
        )
        if inferred_time is not None:
            previous_known_time = inferred_time
        confidence_method = (
            "timeline.rule.v2.inferred"
            if event.event_time_utc is None
            else "timeline.rule.v2.explicit"
        )
        if inferred_reason:
            confidence_method = f"{confidence_method}:{inferred_reason}"
        points.append(
            TimelinePoint(
                point_id=stable_id(prefix="tl", text=f"event:{event.event_id}"),
                source_id=event.event_id,
                source_type="event",
                label=event.summary,
                narrative_order=event.narrative_order,
                actual_time_utc=inferred_time,
                stage=_stage_for_event(
                    event=event, linked_beat=linked_beat, total_events=total_events
                ),
                confidence=ConfidenceScore(method=confidence_method, score=0.78),
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
                actual_time_utc=_coerce_iso_datetime(beat.timestamp_utc),
                stage=beat.stage,
                confidence=ConfidenceScore(method="timeline.rule.v2", score=0.8),
                provenance=ProvenanceRecord(
                    source_segment_ids=beat.evidence_segment_ids,
                    generator="timeline_composer",
                ),
            )
        )

    narrative_sorted = sorted(
        points,
        key=lambda point: (point.narrative_order, point.source_type, point.source_id),
    )
    narrative_order: list[TimelinePoint] = []
    for index, point in enumerate(narrative_sorted, start=1):
        narrative_order.append(point.model_copy(update={"narrative_order": index}))
    actual_time = sorted(
        narrative_order,
        key=lambda point: (
            point.actual_time_utc is None,
            point.actual_time_utc or "",
            point.narrative_order,
            point.source_type,
            point.source_id,
        ),
    )
    conflicts = _detect_timeline_conflicts(narrative=narrative_order)
    consistency_score = _timeline_consistency_score(
        conflicts=conflicts, total_points=len(narrative_order)
    )
    validate_timeline_output(narrative_order)
    return ComposedTimeline(
        actual_time=actual_time,
        narrative_order=narrative_order,
        conflicts=conflicts,
        consistency_score=consistency_score,
    )


def _stage_for_order(order: int, total: int) -> StoryStage:
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


def _linked_beat_for_event(
    *,
    event: ExtractedEvent,
    beats: list[StoryBeat],
    beats_by_segment: dict[str, StoryBeat],
) -> StoryBeat | None:
    linked = beats_by_segment.get(event.segment_id)
    if linked is not None:
        return linked
    if not beats:
        return None
    return min(beats, key=lambda beat: abs(beat.order_index - event.narrative_order))


def _stage_for_event(
    *, event: ExtractedEvent, linked_beat: StoryBeat | None, total_events: int
) -> StoryStage:
    if linked_beat is not None:
        return linked_beat.stage
    return _stage_for_order(event.narrative_order, total_events)


def _coerce_iso_datetime(raw: str | None) -> str | None:
    if raw is None:
        return None
    value = raw.strip()
    if not value:
        return None
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat()


def _summary_time_expression(summary: str) -> str | None:
    match = _ISO_DATE.search(summary)
    if match:
        date_part = match.group("date")
        time_part = match.group("time") or "00:00:00"
        if len(time_part) == 5:
            time_part = f"{time_part}:00"
        return _coerce_iso_datetime(f"{date_part}T{time_part}+00:00")
    normalized = summary.lower()
    base = datetime(2024, 1, 1, tzinfo=UTC)
    if "yesterday" in normalized:
        return (base - timedelta(days=1)).isoformat()
    if "today" in normalized:
        return base.isoformat()
    if "tomorrow" in normalized:
        return (base + timedelta(days=1)).isoformat()
    return None


def _infer_event_time(
    *,
    event: ExtractedEvent,
    linked_beat: StoryBeat | None,
    previous_known_time: str | None,
    narrative_order: int,
) -> tuple[str | None, str | None]:
    explicit = _coerce_iso_datetime(event.event_time_utc)
    if explicit is not None:
        return explicit, None
    from_summary = _summary_time_expression(event.summary)
    if from_summary is not None:
        return from_summary, "summary_expression"
    beat_time = _coerce_iso_datetime(linked_beat.timestamp_utc if linked_beat else None)
    if beat_time is not None:
        return beat_time, "beat_linkage"
    previous = _coerce_iso_datetime(previous_known_time)
    if previous is not None:
        return (
            datetime.fromisoformat(previous) + timedelta(minutes=5)
        ).isoformat(), "sequence_fill"
    synthetic = datetime(2024, 1, 1, tzinfo=UTC) + timedelta(minutes=narrative_order * 5)
    return synthetic.isoformat(), "narrative_anchor"


def _detect_timeline_conflicts(*, narrative: list[TimelinePoint]) -> list[TimelineConflict]:
    conflicts: list[TimelineConflict] = []
    for point in narrative:
        if point.actual_time_utc is None:
            conflicts.append(
                TimelineConflict(
                    conflict_id=stable_id(
                        prefix="tlc", text=f"missing_actual_time:{point.source_id}"
                    ),
                    code="missing_actual_time",
                    severity="warning",
                    message="Timeline point has no resolved actual_time_utc.",
                    source_ids=(point.source_id,),
                )
            )
    known = [point for point in narrative if point.actual_time_utc is not None]
    for previous, current in zip(known, known[1:]):
        prev_time = _coerce_iso_datetime(previous.actual_time_utc)
        current_time = _coerce_iso_datetime(current.actual_time_utc)
        if prev_time is None or current_time is None:
            continue
        if prev_time > current_time:
            conflicts.append(
                TimelineConflict(
                    conflict_id=stable_id(
                        prefix="tlc",
                        text=f"chronology_order_conflict:{previous.source_id}:{current.source_id}",
                    ),
                    code="chronology_order_conflict",
                    severity="error",
                    message=(
                        f"Actual chronology conflicts with narrative order between "
                        f"{previous.source_id} and {current.source_id}."
                    ),
                    source_ids=(previous.source_id, current.source_id),
                )
            )
    return conflicts


def _timeline_consistency_score(*, conflicts: list[TimelineConflict], total_points: int) -> float:
    if total_points <= 0:
        return 1.0
    errors = sum(1 for conflict in conflicts if conflict.severity == "error")
    warnings = sum(1 for conflict in conflicts if conflict.severity == "warning")
    # Chronology order conflicts are high-severity regressions and should weigh heavier than
    # missing-time warnings in consistency calibration.
    penalty = (errors * 1.2) + (warnings * 0.35)
    score = 1.0 - min(1.0, penalty / total_points)
    return round(max(0.0, score), 3)
