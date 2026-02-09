from __future__ import annotations

from story_gen.core.dashboard_views import build_dashboard_read_model
from story_gen.core.quality_evaluation import evaluate_quality_gate
from story_gen.core.story_schema import (
    ConfidenceScore,
    ExtractedEvent,
    Insight,
    ProvenanceRecord,
    QualityGate,
    RawSegment,
    StoryBeat,
    StoryDocument,
)
from story_gen.core.timeline_composer import compose_timeline


def _segment(segment_id: str, index: int) -> RawSegment:
    return RawSegment(
        segment_id=segment_id,
        source_type="text",
        original_text="Segment text.",
        normalized_text="Segment text.",
        translated_text="Segment text.",
        language_code="en",
        segment_index=index,
        char_start=(index - 1) * 20,
        char_end=(index - 1) * 20 + 12,
    )


def _event(
    *,
    event_id: str,
    segment_id: str,
    order: int,
    summary: str,
    event_time_utc: str | None,
) -> ExtractedEvent:
    return ExtractedEvent(
        event_id=event_id,
        summary=summary,
        segment_id=segment_id,
        narrative_order=order,
        event_time_utc=event_time_utc,
        entity_names=["rhea"],
        confidence=ConfidenceScore(method="event.rule.v1", score=0.8),
        provenance=ProvenanceRecord(
            source_segment_ids=[segment_id],
            generator="event_extractor",
        ),
    )


def _beat(
    *,
    beat_id: str,
    order: int,
    stage: str,
    segment_id: str,
    timestamp_utc: str | None,
) -> StoryBeat:
    return StoryBeat(
        beat_id=beat_id,
        stage=stage,  # type: ignore[arg-type]
        order_index=order,
        summary=f"{stage} beat",
        timestamp_utc=timestamp_utc,
        evidence_segment_ids=[segment_id],
        confidence=ConfidenceScore(method="beat.rule.v1", score=0.8),
        provenance=ProvenanceRecord(
            source_segment_ids=[segment_id],
            generator="beat_detector",
        ),
    )


def test_timeline_composer_uses_beat_linkage_stage_and_infers_missing_time() -> None:
    events = [
        _event(
            event_id="evt_1",
            segment_id="seg_001",
            order=1,
            summary="On 2024-04-10 Rhea finds the ledger.",
            event_time_utc=None,
        ),
        _event(
            event_id="evt_2",
            segment_id="seg_002",
            order=2,
            summary="She confronts the council in the hall.",
            event_time_utc=None,
        ),
    ]
    beats = [
        _beat(
            beat_id="beat_1",
            order=1,
            stage="setup",
            segment_id="seg_001",
            timestamp_utc="2024-04-10T00:00:00+00:00",
        ),
        _beat(
            beat_id="beat_2",
            order=2,
            stage="climax",
            segment_id="seg_002",
            timestamp_utc=None,
        ),
    ]
    timeline = compose_timeline(events=events, beats=beats)
    event_points = [point for point in timeline.narrative_order if point.source_type == "event"]
    assert event_points[0].stage == "setup"
    assert event_points[1].stage == "climax"
    assert event_points[0].actual_time_utc is not None
    assert event_points[1].actual_time_utc is not None
    assert event_points[1].confidence.method.startswith("timeline.rule.v2.inferred")


def test_timeline_composer_reports_chronology_order_conflict() -> None:
    events = [
        _event(
            event_id="evt_1",
            segment_id="seg_001",
            order=1,
            summary="Rhea speaks first.",
            event_time_utc="2024-02-03T10:00:00+00:00",
        ),
        _event(
            event_id="evt_2",
            segment_id="seg_002",
            order=2,
            summary="Rhea speaks second.",
            event_time_utc="2024-02-03T09:00:00+00:00",
        ),
    ]
    beats = [
        _beat(
            beat_id="beat_1",
            order=1,
            stage="setup",
            segment_id="seg_001",
            timestamp_utc=None,
        ),
        _beat(
            beat_id="beat_2",
            order=2,
            stage="escalation",
            segment_id="seg_002",
            timestamp_utc=None,
        ),
    ]
    timeline = compose_timeline(events=events, beats=beats)
    assert any(conflict.code == "chronology_order_conflict" for conflict in timeline.conflicts)
    assert timeline.consistency_score < 1.0


def test_dashboard_timeline_lanes_surface_diagnostics_flags() -> None:
    segments = [_segment("seg_001", 1), _segment("seg_002", 2)]
    events = [
        _event(
            event_id="evt_1",
            segment_id="seg_001",
            order=1,
            summary="First event",
            event_time_utc="2024-02-03T10:00:00+00:00",
        ),
        _event(
            event_id="evt_2",
            segment_id="seg_002",
            order=2,
            summary="Second event",
            event_time_utc="2024-02-03T09:00:00+00:00",
        ),
    ]
    beats = [
        _beat(
            beat_id="beat_1",
            order=1,
            stage="setup",
            segment_id="seg_001",
            timestamp_utc=None,
        ),
        _beat(
            beat_id="beat_2",
            order=2,
            stage="escalation",
            segment_id="seg_002",
            timestamp_utc=None,
        ),
    ]
    timeline = compose_timeline(events=events, beats=beats)
    quality_gate = QualityGate(
        passed=True,
        confidence_floor=0.8,
        hallucination_risk=0.0,
        translation_quality=1.0,
        reasons=[],
    )
    document = StoryDocument(
        story_id="story-1",
        source_language="en",
        target_language="en",
        raw_segments=segments,
        extracted_events=events,
        story_beats=beats,
        theme_signals=[],
        entity_mentions=[],
        timeline_points=timeline.narrative_order,
        insights=[],
        quality_gate=quality_gate,
    )
    model = build_dashboard_read_model(
        document=document,
        arcs=[],
        conflicts=[],
        emotions=[],
        timeline_actual=timeline.actual_time,
        timeline_narrative=timeline.narrative_order,
        timeline_conflicts=timeline.conflicts,
    )
    diagnostics_lane = next(
        (lane for lane in model.timeline_lanes if lane.lane == "timeline_diagnostics"),
        None,
    )
    assert diagnostics_lane is not None
    narrative_lane = next(lane for lane in model.timeline_lanes if lane.lane == "narrative_order")
    assert any(item["discrepancy_flags"] for item in narrative_lane.items)


def test_quality_gate_includes_timeline_consistency_signal() -> None:
    segments = [_segment("seg_001", 1)]
    insights = [
        Insight(
            insight_id="insight_1",
            granularity="macro",
            title="t",
            content="c",
            stage=None,
            beat_id=None,
            evidence_segment_ids=["seg_001"],
            confidence=ConfidenceScore(method="rule", score=0.8),
            provenance=ProvenanceRecord(source_segment_ids=["seg_001"], generator="insight_engine"),
        )
    ]
    gate, metrics = evaluate_quality_gate(
        segments=segments,
        insights=insights,
        timeline_consistency=0.2,
    )
    assert gate.passed is False
    assert "timeline_consistency_low" in gate.reasons
    assert metrics.timeline_consistency == 0.2
