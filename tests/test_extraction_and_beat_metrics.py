from __future__ import annotations

from typing import Any

from story_gen.core.narrative_analysis import detect_story_beats
from story_gen.core.story_extraction import extract_events_and_entities_with_diagnostics
from story_gen.core.story_schema import RawSegment, stable_id


def _segment(text: str, index: int) -> RawSegment:
    return RawSegment(
        segment_id=stable_id(prefix="seg", text=f"gold:{index}:{text}"),
        source_type="text",
        original_text=text,
        normalized_text=text,
        translated_text=text,
        language_code="en",
        segment_index=index,
        char_start=(index - 1) * 80,
        char_end=(index - 1) * 80 + len(text),
    )


def _gold_segments() -> list[RawSegment]:
    return [
        _segment("Rhea enters the archive and recovers a hidden ledger.", 1),
        _segment("Council members deny the record and trigger conflict.", 2),
        _segment("Rhea confronts the council and reveals matching signatures.", 3),
        _segment("The city accepts the evidence and begins to heal.", 4),
    ]


def test_extraction_precision_recall_and_beat_stage_agreement_are_measured() -> None:
    segments = _gold_segments()
    expected_event_keywords = [
        {"archive", "ledger"},
        {"deny", "record", "conflict"},
        {"confronts", "reveals"},
        {"accepts", "heal"},
    ]
    expected_stage_sequence = ["setup", "escalation", "climax", "resolution"]

    events, entities, diagnostics = extract_events_and_entities_with_diagnostics(segments=segments)
    beats = detect_story_beats(events=events)

    matched_events = 0
    for event, keywords in zip(events, expected_event_keywords):
        lowered = event.summary.lower()
        if any(keyword in lowered for keyword in keywords):
            matched_events += 1
    extraction_precision = matched_events / max(1, len(events))
    extraction_recall = matched_events / len(expected_event_keywords)
    stage_matches = sum(
        1
        for actual, expected in zip((beat.stage for beat in beats), expected_stage_sequence)
        if actual == expected
    )
    beat_stage_agreement = stage_matches / len(expected_stage_sequence)

    assert diagnostics.fallback_used is False
    assert extraction_precision >= 0.75
    assert extraction_recall >= 0.75
    assert beat_stage_agreement >= 0.75
    assert all(beat.evidence_segment_ids for beat in beats)
    assert entities


def test_extraction_failure_falls_back_with_confidence_downgrade(monkeypatch: Any) -> None:
    monkeypatch.setenv("STORY_GEN_EXTRACTION_FORCE_FAIL", "1")
    events, entities, diagnostics = extract_events_and_entities_with_diagnostics(
        segments=_gold_segments()
    )

    assert diagnostics.fallback_used is True
    assert diagnostics.provider == "rule_fallback.v1"
    assert {issue.code for issue in diagnostics.issues} >= {
        "extraction_provider_failed",
        "extraction_fallback_used",
    }
    assert all(event.confidence.score <= 0.52 for event in events)
    assert all(entity.confidence.score <= 0.66 for entity in entities)
