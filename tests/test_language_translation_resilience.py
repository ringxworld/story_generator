from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from story_gen.core.language_translation import translate_segments_with_diagnostics
from story_gen.core.story_schema import RawSegment, stable_id

FIXTURE_PATH = Path("tests/fixtures/non_english_translation_corpus.v1.json")


def _segment(text: str, index: int) -> RawSegment:
    return RawSegment(
        segment_id=stable_id(prefix="seg", text=f"translation:{index}:{text}"),
        source_type="text",
        original_text=text,
        normalized_text=text,
        translated_text=None,
        language_code="und",
        segment_index=index,
        char_start=(index - 1) * 50,
        char_end=(index - 1) * 50 + len(text),
    )


def test_non_english_translation_corpus_is_deterministic() -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    cases = payload["cases"]
    segments = [_segment(case["text"], index) for index, case in enumerate(cases, start=1)]

    first = translate_segments_with_diagnostics(segments=segments, target_language="en")
    second = translate_segments_with_diagnostics(segments=segments, target_language="en")

    first_segments, first_alignments, first_source, first_diag = first
    second_segments, second_alignments, second_source, second_diag = second

    assert [segment.translated_text for segment in first_segments] == [
        segment.translated_text for segment in second_segments
    ]
    assert [alignment.method for alignment in first_alignments] == [
        alignment.method for alignment in second_alignments
    ]
    assert [alignment.quality_score for alignment in first_alignments] == [
        alignment.quality_score for alignment in second_alignments
    ]
    assert first_source == second_source
    assert first_diag.provider == "lexicon.v2"
    assert second_diag.provider == "lexicon.v2"

    assert first_segments[0].language_code == "es"
    assert first_segments[1].language_code == "fr"
    assert first_segments[2].language_code == "ja"
    assert first_segments[2].translated_text == cases[2]["text"]
    assert first_alignments[2].quality_score < 0.5

    for index, case in enumerate(cases):
        translated = first_segments[index].translated_text or ""
        for token in case["expected_translated_contains"]:
            assert token in translated.lower()


def test_translation_provider_failure_uses_fallback_with_diagnostics(monkeypatch: Any) -> None:
    monkeypatch.setenv("STORY_GEN_TRANSLATION_PROVIDER", "failing")
    monkeypatch.setenv("STORY_GEN_TRANSLATION_RETRY_COUNT", "1")
    segment = _segment("La historia de la familia cambia.", 1)

    translated, alignments, source_language, diagnostics = translate_segments_with_diagnostics(
        segments=[segment],
        target_language="en",
    )

    assert source_language == "es"
    assert translated[0].translated_text is not None
    assert "story" in translated[0].translated_text.lower()
    assert diagnostics.fallback_used is True
    assert diagnostics.degraded_segments == 1
    assert diagnostics.issue_count >= 2
    assert {issue.code for issue in diagnostics.issues} >= {
        "translation_provider_attempt_failed",
        "translation_provider_fallback_used",
    }
    assert alignments[0].method == "fallback.lexicon.v1"
