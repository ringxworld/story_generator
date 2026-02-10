from __future__ import annotations

from story_gen.core.quality_evaluation import evaluate_quality_gate
from story_gen.core.story_schema import ConfidenceScore, Insight, ProvenanceRecord, RawSegment


def _segment() -> RawSegment:
    text = "Rhea opens the archive ledger and confirms the memory record."
    return RawSegment(
        segment_id="seg_001",
        source_type="text",
        original_text=text,
        normalized_text=text,
        translated_text=text,
        language_code="en",
        segment_index=1,
        char_start=0,
        char_end=len(text),
    )


def _insight(*, insight_id: str, content: str) -> Insight:
    return Insight(
        insight_id=insight_id,
        granularity="macro",
        title="Insight",
        content=content,
        stage=None,
        beat_id=None,
        evidence_segment_ids=["seg_001"],
        confidence=ConfidenceScore(method="insight.test.v1", score=0.9),
        provenance=ProvenanceRecord(source_segment_ids=["seg_001"], generator="test"),
    )


def test_quality_gate_rejects_insights_with_inconsistent_evidence() -> None:
    gate, metrics = evaluate_quality_gate(
        segments=[_segment()],
        insights=[
            _insight(insight_id="ins_bad", content="Orbital trade routes collapse overnight.")
        ],
        timeline_consistency=1.0,
    )

    assert gate.passed is False
    assert "insight_evidence_inconsistent" in gate.reasons
    assert metrics.inconsistent_insight_ids == ("ins_bad",)


def test_quality_gate_accepts_grounded_insights() -> None:
    gate, metrics = evaluate_quality_gate(
        segments=[_segment()],
        insights=[
            _insight(
                insight_id="ins_good",
                content="Rhea confirms the archive ledger memory record.",
            )
        ],
        timeline_consistency=1.0,
    )

    assert gate.passed is True
    assert "insight_evidence_inconsistent" not in gate.reasons
    assert metrics.inconsistent_insight_ids == ()
