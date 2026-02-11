from __future__ import annotations

from story_gen.core.essence_extraction import (
    extract_essence_from_fragment,
    extract_essence_from_segments,
)
from story_gen.core.story_schema import (
    ConfidenceScore,
    EntityMention,
    ExtractedEvent,
    ProvenanceRecord,
    RawSegment,
)


def _segment(*, segment_id: str, index: int, text: str) -> RawSegment:
    return RawSegment(
        segment_id=segment_id,
        source_type="text",
        original_text=text,
        normalized_text=text,
        language_code="en",
        translated_text=text,
        segment_index=index,
        char_start=0,
        char_end=max(1, len(text)),
    )


def _character_mention(*, name: str, segment_ids: list[str]) -> EntityMention:
    return EntityMention(
        entity_id=f"ent_{name.lower()}",
        name=name.lower(),
        entity_type="character",
        mention_count=len(segment_ids),
        segment_ids=segment_ids,
        confidence=ConfidenceScore(method="test", score=0.9),
        provenance=ProvenanceRecord(
            source_segment_ids=segment_ids,
            generator="test",
        ),
    )


def _event(*, event_id: str, segment_id: str, summary: str, order: int) -> ExtractedEvent:
    return ExtractedEvent(
        event_id=event_id,
        summary=summary,
        segment_id=segment_id,
        narrative_order=order,
        event_time_utc=None,
        entity_names=[],
        confidence=ConfidenceScore(method="test", score=0.8),
        provenance=ProvenanceRecord(
            source_segment_ids=[segment_id],
            generator="test",
        ),
    )


def test_extract_essence_from_fragment_detects_expected_scene_traits() -> None:
    fragment = extract_essence_from_fragment(
        text=(
            "In the dark archive, I wondered who hid the cipher. "
            "Shadows moved while I feared the unknown."
        )
    )
    assert "dark" in fragment.tone_tags
    assert "introspective" in fragment.tone_tags
    assert "mysterious" in fragment.tone_tags
    assert "sparse-dialogue" in fragment.tone_tags
    assert fragment.mystery_level > 0.0
    assert "Scene essence:" in fragment.generation_guidance


def test_extract_essence_from_segments_builds_character_profiles_and_constraints() -> None:
    segments = [
        _segment(
            segment_id="seg001",
            index=1,
            text="Rhea was afraid but vowed to continue and learn from the failure.",
        ),
        _segment(
            segment_id="seg002",
            index=2,
            text='Rhea said, "I will persist." She studied the archive and adapted quickly.',
        ),
    ]
    entities = [_character_mention(name="rhea", segment_ids=["seg001", "seg002"])]
    details = extract_essence_from_segments(segments=segments, entities=entities, events=[])

    assert details.character_profiles
    profile = details.character_profiles[0]
    assert profile.character_name == "rhea"
    assert profile.consistency_score >= 0.5
    assert any(
        trait in profile.essence_traits for trait in {"vulnerable", "determined", "growth-oriented"}
    )
    assert details.character_constraints
    assert "consistency(rhea)" in details.character_constraints[0].constraint_expression


def test_extract_essence_from_segments_builds_world_profile_evolution_and_alignment() -> None:
    segments = [
        _segment(
            segment_id="seg010",
            index=1,
            text="The council protected the old ritual while the temple bells echoed.",
        ),
        _segment(
            segment_id="seg011",
            index=2,
            text="An arcane rune flared above the archive as secret sigils moved.",
        ),
        _segment(
            segment_id="seg012",
            index=3,
            text="A signal protocol activated the engine and network drones.",
        ),
        _segment(
            segment_id="seg013",
            index=4,
            text="The guild debated customs and law while the hidden cipher surfaced.",
        ),
    ]
    events = [
        _event(
            event_id="evt_1",
            segment_id="seg011",
            summary="A rune ritual exposed the hidden mystery.",
            order=1,
        ),
        _event(
            event_id="evt_2",
            segment_id="seg012",
            summary="The engine signal protocol launched the drones.",
            order=2,
        ),
    ]
    details = extract_essence_from_segments(segments=segments, entities=[], events=events)

    assert details.world.magic_level > 0.0
    assert details.world.tech_level > 0.0
    assert details.world.culture_density > 0.0
    assert len(details.world_evolution) == 4
    assert details.event_world_alignment > 0.0
    assert any(stage.descriptor for stage in details.world_evolution)
