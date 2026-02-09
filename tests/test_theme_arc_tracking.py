from __future__ import annotations

from story_gen.core.story_schema import (
    ConfidenceScore,
    EntityMention,
    ProvenanceRecord,
    StoryBeat,
    StoryStage,
)
from story_gen.core.theme_arc_tracking import track_theme_arc_signals


def _beat(
    *, beat_id: str, stage: StoryStage, index: int, summary: str, segment_id: str
) -> StoryBeat:
    return StoryBeat(
        beat_id=beat_id,
        stage=stage,
        order_index=index,
        summary=summary,
        timestamp_utc=None,
        evidence_segment_ids=[segment_id],
        confidence=ConfidenceScore(method="test", score=0.9),
        provenance=ProvenanceRecord(
            source_segment_ids=[segment_id],
            generator="test_fixture",
        ),
    )


def _entity(*, entity_id: str, name: str, segment_ids: list[str]) -> EntityMention:
    return EntityMention(
        entity_id=entity_id,
        name=name,
        entity_type="character",
        mention_count=len(segment_ids),
        segment_ids=segment_ids,
        confidence=ConfidenceScore(method="test", score=0.85),
        provenance=ProvenanceRecord(
            source_segment_ids=segment_ids,
            generator="test_fixture",
        ),
    )


def test_theme_tracking_captures_strengthening_then_fading_with_evidence() -> None:
    beats = [
        _beat(
            beat_id="beat_setup",
            stage="setup",
            index=1,
            summary="Rhea preserves memory in an archive.",
            segment_id="seg-01",
        ),
        _beat(
            beat_id="beat_escalation",
            stage="escalation",
            index=2,
            summary="The dispute intensifies as memory remember archive history record ledger.",
            segment_id="seg-02",
        ),
        _beat(
            beat_id="beat_climax",
            stage="climax",
            index=3,
            summary="At climax the crowd remembers, but trust is fractured by conflict.",
            segment_id="seg-03",
        ),
        _beat(
            beat_id="beat_resolution",
            stage="resolution",
            index=4,
            summary="The city accepts truth and begins to heal with renewed trust.",
            segment_id="seg-04",
        ),
    ]
    entities = [_entity(entity_id="ent_rhea", name="rhea", segment_ids=["seg-01", "seg-02"])]

    themes, arcs, conflicts, emotions = track_theme_arc_signals(beats=beats, entities=entities)

    memory_signals = [signal for signal in themes if signal.label == "memory"]
    assert [signal.stage for signal in memory_signals] == [
        "setup",
        "escalation",
        "climax",
        "resolution",
    ]
    assert memory_signals[0].direction == "emerging"
    assert memory_signals[1].direction == "strengthening"
    assert memory_signals[2].direction == "fading"
    assert memory_signals[3].direction in {"fading", "steady"}
    assert memory_signals[1].strength > memory_signals[0].strength > memory_signals[2].strength
    assert memory_signals[3].strength <= memory_signals[2].strength
    for signal in memory_signals:
        assert signal.evidence_segment_ids
        assert signal.provenance.source_segment_ids
        assert set(signal.evidence_segment_ids).intersection(signal.provenance.source_segment_ids)
        assert signal.confidence.score > 0.0

    assert len(arcs) == 4
    assert any(arc.state == "fading" for arc in arcs)
    assert all(arc.evidence_segment_ids for arc in arcs)
    assert all(arc.provenance_segment_ids for arc in arcs)
    assert all(
        set(arc.evidence_segment_ids).intersection(arc.provenance_segment_ids) for arc in arcs
    )
    assert all(arc.confidence > 0.0 for arc in arcs)

    assert len(conflicts) == 3
    assert all(conflict.evidence_segment_ids for conflict in conflicts)
    assert all(conflict.provenance_segment_ids for conflict in conflicts)
    assert all(
        set(conflict.evidence_segment_ids).intersection(conflict.provenance_segment_ids)
        for conflict in conflicts
    )
    assert all(conflict.confidence > 0.0 for conflict in conflicts)

    assert len(emotions) == 4
    assert all(emotion.evidence_segment_ids for emotion in emotions)
    assert all(emotion.provenance_segment_ids for emotion in emotions)
    assert all(
        set(emotion.evidence_segment_ids).intersection(emotion.provenance_segment_ids)
        for emotion in emotions
    )
    assert all(emotion.confidence > 0.0 for emotion in emotions)
