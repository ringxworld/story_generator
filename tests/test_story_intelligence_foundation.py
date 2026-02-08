from __future__ import annotations

import pytest

from story_gen.core.language_translation import detect_language, translate_segments
from story_gen.core.pipeline_contracts import (
    validate_beat_output,
    validate_extraction_input,
    validate_extraction_output,
    validate_insight_output,
)
from story_gen.core.story_ingestion import IngestionRequest, ingest_story_text
from story_gen.core.story_schema import (
    ConfidenceScore,
    ExtractedEvent,
    Insight,
    ProvenanceRecord,
    RawSegment,
    StoryBeat,
)


def _sample_segment(segment_id: str, index: int) -> RawSegment:
    return RawSegment(
        segment_id=segment_id,
        source_type="text",
        original_text="Rhea uncovers a hidden archive.",
        normalized_text="Rhea uncovers a hidden archive.",
        language_code="en",
        translated_text="Rhea uncovers a hidden archive.",
        segment_index=index,
        char_start=(index - 1) * 10,
        char_end=(index - 1) * 10 + 9,
    )


def test_ingestion_normalizes_and_chunks_deterministically() -> None:
    request = IngestionRequest(
        source_type="text",
        source_text="  First paragraph.\n\nSecond  paragraph with\tspaces.  ",
        idempotency_key="story-a",
    )
    first = ingest_story_text(request)
    second = ingest_story_text(request)
    assert first.source_hash == second.source_hash
    assert first.dedupe_key == second.dedupe_key
    assert [segment.segment_id for segment in first.segments] == [
        segment.segment_id for segment in second.segments
    ]
    assert first.normalized_text == "First paragraph.\n\nSecond paragraph with spaces."


def test_language_detection_and_translation_attach_alignment() -> None:
    segment = RawSegment(
        segment_id="seg_testone",
        source_type="text",
        original_text="La historia habla de una familia.",
        normalized_text="La historia habla de una familia.",
        language_code="und",
        translated_text=None,
        segment_index=1,
        char_start=0,
        char_end=33,
    )
    detected = detect_language(segment.normalized_text)
    assert detected.language_code == "es"

    translated, alignments, source_language = translate_segments(
        segments=[segment], target_language="en"
    )
    assert source_language == "es"
    assert translated[0].translated_text is not None
    assert "story" in translated[0].translated_text
    assert len(alignments) == 1
    assert alignments[0].source_segment_id == segment.segment_id


def test_language_detection_identifies_japanese_text() -> None:
    text = "これは危険な匂いがする。スバルは記憶を辿る。"
    detected = detect_language(text)
    assert detected.language_code == "ja"
    assert detected.confidence >= 0.8


def test_pipeline_contracts_reject_invalid_sequences() -> None:
    segment = _sample_segment("seg_one", 1)
    validate_extraction_input([segment])

    event = ExtractedEvent(
        event_id="evt_one",
        summary="Rhea finds the archive.",
        segment_id=segment.segment_id,
        narrative_order=1,
        event_time_utc=None,
        entity_names=["rhea"],
        confidence=ConfidenceScore(method="rule.v1", score=0.8),
        provenance=ProvenanceRecord(
            source_segment_ids=[segment.segment_id],
            generator="event_extractor",
        ),
    )
    validate_extraction_output([event])

    bad_beat = StoryBeat(
        beat_id="beat_one",
        stage="setup",
        order_index=2,
        summary="Setup beat.",
        timestamp_utc=None,
        evidence_segment_ids=[segment.segment_id],
        confidence=ConfidenceScore(method="rule.v1", score=0.7),
        provenance=ProvenanceRecord(
            source_segment_ids=[segment.segment_id], generator="beat_detector"
        ),
    )
    with pytest.raises(ValueError, match="contiguous"):
        validate_beat_output([bad_beat])


def test_insight_contract_requires_positive_confidence() -> None:
    insight = Insight(
        insight_id="ins_one",
        granularity="macro",
        title="Core thesis",
        content="Memory and truth collide.",
        stage=None,
        beat_id=None,
        evidence_segment_ids=["seg_one"],
        confidence=ConfidenceScore(method="rule.v1", score=0.0),
        provenance=ProvenanceRecord(source_segment_ids=["seg_one"], generator="insight_engine"),
    )
    with pytest.raises(ValueError, match="positive"):
        validate_insight_output([insight])
