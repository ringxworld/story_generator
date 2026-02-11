from __future__ import annotations

from story_gen.core.dialogue_extraction import extract_dialogue_details
from story_gen.core.story_schema import RawSegment


def _segment(*, segment_id: str, text: str) -> RawSegment:
    return RawSegment(
        segment_id=segment_id,
        source_type="text",
        original_text=text,
        normalized_text=text,
        language_code="en",
        translated_text=text,
        segment_index=1,
        char_start=0,
        char_end=max(1, len(text)),
    )


def test_extract_dialogue_details_parses_turns_and_internal_monologue() -> None:
    segments = [
        _segment(segment_id="seg001", text="Rhea: We move now."),
        _segment(segment_id="seg002", text='"Hold the gate," said Rhea.'),
        _segment(
            segment_id="seg003",
            text="I thought we were finished, but I refused to surrender.",
        ),
    ]

    details = extract_dialogue_details(segments=segments, known_character_names=["rhea"])

    assert len(details.dialogue_turns) == 2
    assert details.dialogue_turns[0].speaker == "rhea"
    assert details.dialogue_turns[0].attribution_method == "transcript_prefix"
    assert details.dialogue_turns[1].speaker == "rhea"
    assert details.dialogue_turns[1].attribution_method == "narrative_after_quote"
    assert details.internal_monologues
    assert details.internal_monologues[0].segment_id == "seg003"
    assert details.dominant_mode_by_segment["seg001"] == "dialogue"
    assert details.dominant_mode_by_segment["seg003"] == "monologue"
    assert details.narrative_balance.dialogue_ratio > 0
    assert details.narrative_balance.monologue_ratio > 0


def test_extract_dialogue_details_unknown_speaker_and_no_cues() -> None:
    segments = [
        _segment(segment_id="seg010", text='"Retreat now," said Commander.'),
        _segment(
            segment_id="seg011",
            text="The archive was founded long ago and was known for rigid customs.",
        ),
    ]

    details = extract_dialogue_details(segments=segments, known_character_names=["rhea"])

    assert details.dialogue_turns
    assert details.dialogue_turns[0].speaker == "unknown"
    assert details.internal_monologues == []
    assert details.dominant_mode_by_segment["seg011"] == "exposition"


def test_extract_dialogue_details_handles_malformed_quotes_without_crashing() -> None:
    segments = [
        _segment(
            segment_id="seg020",
            text='Rhea said "We should move quickly before dawn and then paused abruptly',
        ),
        _segment(
            segment_id="seg021",
            text="They rushed down the corridor and jumped over shattered stone.",
        ),
    ]

    details = extract_dialogue_details(segments=segments, known_character_names=["rhea"])

    assert details.dialogue_turns == []
    assert details.dominant_mode_by_segment["seg020"] in {"exposition", "action"}
    assert details.dominant_mode_by_segment["seg021"] == "action"
