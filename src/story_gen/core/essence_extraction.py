"""Deterministic literary essence extraction across narrative fragments and stories."""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

from story_gen.core.dialogue_extraction import extract_dialogue_details
from story_gen.core.story_schema import STORY_STAGE_ORDER, EntityMention, ExtractedEvent, RawSegment

_WORD_PATTERN = re.compile(r"[A-Za-z']+")
_FIRST_PERSON_PATTERN = re.compile(r"\b(i|me|my|mine|myself)\b", flags=re.IGNORECASE)
_THOUGHT_VERB_PATTERN = re.compile(
    r"\b(think|thought|wonder|wondered|remember|remembered|realize|realized|"
    r"fear|feared|hope|hoped|dream|dreamed|question|questioned)\b",
    flags=re.IGNORECASE,
)

_DARK_TONE_KEYWORDS = {
    "dark",
    "bleak",
    "grim",
    "fear",
    "dread",
    "shadow",
    "blood",
    "cold",
    "void",
    "despair",
    "haunt",
    "haunted",
}
_MYSTERY_KEYWORDS = {
    "mystery",
    "mysterious",
    "unknown",
    "hidden",
    "secret",
    "clue",
    "cipher",
    "enigma",
    "whisper",
    "rumor",
}
_WARM_TONE_KEYWORDS = {
    "hope",
    "healing",
    "kind",
    "comfort",
    "light",
    "trust",
    "peace",
    "joy",
    "calm",
}
_MAGIC_KEYWORDS = {
    "magic",
    "spell",
    "rune",
    "sorcery",
    "arcane",
    "mana",
    "enchanted",
    "curse",
    "ritual",
}
_TECH_KEYWORDS = {
    "device",
    "engine",
    "algorithm",
    "circuit",
    "drone",
    "robot",
    "network",
    "signal",
    "code",
    "protocol",
}
_CULTURE_KEYWORDS = {
    "tradition",
    "festival",
    "council",
    "archive",
    "custom",
    "ceremony",
    "law",
    "clan",
    "guild",
    "temple",
}
_CHARACTER_TRAIT_LEXICONS: dict[str, set[str]] = {
    "vulnerable": {
        "fear",
        "afraid",
        "hurt",
        "wound",
        "fragile",
        "shaking",
        "doubt",
        "hesitate",
    },
    "growth-oriented": {
        "learn",
        "adapt",
        "improve",
        "change",
        "practice",
        "training",
        "study",
        "grow",
    },
    "determined": {
        "resolve",
        "vow",
        "persist",
        "insist",
        "refuse",
        "continue",
        "endure",
        "commit",
    },
    "compassionate": {
        "help",
        "protect",
        "care",
        "comfort",
        "rescue",
        "save",
        "support",
    },
    "cunning": {
        "plan",
        "scheme",
        "trick",
        "deceive",
        "bait",
        "manipulate",
    },
}


@dataclass(frozen=True)
class FragmentEssence:
    """Essence profile for one scene, fragment, or full story body."""

    tone_tags: list[str]
    dialogue_density: float
    introspection_level: float
    mystery_level: float
    descriptors: list[str]
    generation_guidance: str


@dataclass(frozen=True)
class CharacterEssenceProfile:
    """Essence profile for one tracked character."""

    character_name: str
    essence_traits: list[str]
    consistency_score: float
    evidence_segment_ids: list[str]


@dataclass(frozen=True)
class CharacterEssenceConstraint:
    """Constraint expression used to preserve character essence during generation."""

    character_name: str
    required_traits: list[str]
    minimum_consistency: float
    constraint_expression: str


@dataclass(frozen=True)
class WorldEssenceProfile:
    """Story-world essence vector."""

    magic_level: float
    tech_level: float
    culture_density: float
    mystery_level: float
    descriptors: list[str]


@dataclass(frozen=True)
class WorldStageSnapshot:
    """World essence progression for one stage."""

    stage: str
    magic_level: float
    tech_level: float
    culture_density: float
    mystery_level: float
    descriptor: str


@dataclass(frozen=True)
class EssenceExtractionDetails:
    """Combined essence extraction details used by downstream pipeline consumers."""

    segment_ids: list[str]
    fragment: FragmentEssence
    world: WorldEssenceProfile
    world_evolution: list[WorldStageSnapshot]
    character_profiles: list[CharacterEssenceProfile]
    character_constraints: list[CharacterEssenceConstraint]
    event_world_alignment: float


def extract_essence_from_segments(
    *,
    segments: list[RawSegment],
    entities: list[EntityMention],
    events: list[ExtractedEvent] | None = None,
) -> EssenceExtractionDetails:
    """Extract fragment, character, and world essence from normalized segments."""
    segment_texts: dict[str, str] = {}
    for segment in segments:
        text = (segment.translated_text or segment.normalized_text).strip()
        if text:
            segment_texts[segment.segment_id] = text
    segment_ids = list(segment_texts.keys())
    dialogue = extract_dialogue_details(segments=segments)

    fragment = _build_fragment_essence(
        segment_texts=segment_texts, dialogue_density=dialogue.narrative_balance.dialogue_ratio
    )
    world = _build_world_essence(texts=list(segment_texts.values()))
    world_evolution = _build_world_evolution(texts=list(segment_texts.values()))
    character_profiles = _build_character_profiles(segment_texts=segment_texts, entities=entities)
    character_constraints = [
        CharacterEssenceConstraint(
            character_name=profile.character_name,
            required_traits=list(profile.essence_traits),
            minimum_consistency=max(0.55, round(profile.consistency_score - 0.1, 2)),
            constraint_expression=(
                f"consistency({profile.character_name}) >= "
                f"{max(0.55, round(profile.consistency_score - 0.1, 2)):.2f} "
                f"AND preserve_traits({profile.character_name}, {', '.join(profile.essence_traits)})"
            ),
        )
        for profile in character_profiles
    ]
    event_world_alignment = _score_event_world_alignment(
        events=events or [],
        world=world,
    )
    return EssenceExtractionDetails(
        segment_ids=segment_ids,
        fragment=fragment,
        world=world,
        world_evolution=world_evolution,
        character_profiles=character_profiles,
        character_constraints=character_constraints,
        event_world_alignment=event_world_alignment,
    )


def extract_essence_from_fragment(*, text: str) -> FragmentEssence:
    """Extract essence from one scene/fragment text payload."""
    normalized = text.strip()
    if not normalized:
        return FragmentEssence(
            tone_tags=["neutral"],
            dialogue_density=0.0,
            introspection_level=0.0,
            mystery_level=0.0,
            descriptors=["neutral-tone", "minimal-dialogue", "low-introspection", "low-mystery"],
            generation_guidance=(
                "Use a neutral tone baseline, then add explicit tone and world cues before generation."
            ),
        )
    segment = RawSegment(
        segment_id="seg_fragment",
        source_type="text",
        original_text=normalized,
        normalized_text=normalized,
        language_code="en",
        translated_text=normalized,
        segment_index=1,
        char_start=0,
        char_end=max(1, len(normalized)),
    )
    details = extract_essence_from_segments(segments=[segment], entities=[], events=[])
    return details.fragment


def _build_fragment_essence(
    *,
    segment_texts: dict[str, str],
    dialogue_density: float,
) -> FragmentEssence:
    texts = list(segment_texts.values())
    tokens = _tokenize_texts(texts)
    dark_score = _keyword_score(tokens=tokens, keywords=_DARK_TONE_KEYWORDS)
    warm_score = _keyword_score(tokens=tokens, keywords=_WARM_TONE_KEYWORDS)
    mystery_score = _keyword_score(tokens=tokens, keywords=_MYSTERY_KEYWORDS)
    introspection_score = _introspection_score(texts=texts)
    tone_tags: list[str] = []
    if dark_score >= 0.35:
        tone_tags.append("dark")
    if warm_score >= 0.35:
        tone_tags.append("warm")
    if mystery_score >= 0.33:
        tone_tags.append("mysterious")
    if introspection_score >= 0.33:
        tone_tags.append("introspective")
    if dialogue_density <= 0.25:
        tone_tags.append("sparse-dialogue")
    if not tone_tags:
        tone_tags.append("neutral")
    descriptors = [
        ("dark-tone" if dark_score >= 0.35 else "balanced-tone"),
        ("sparse-dialogue" if dialogue_density <= 0.25 else "dialogue-forward"),
        ("high-introspection" if introspection_score >= 0.4 else "low-introspection"),
        ("mysterious" if mystery_score >= 0.33 else "clear-surface"),
    ]
    guidance = (
        f"Scene essence: {', '.join(tone_tags)}. Maintain dialogue density around {dialogue_density:.2f}, "
        f"introspection level {introspection_score:.2f}, and mystery level {mystery_score:.2f} "
        f"when drafting the next continuation."
    )
    return FragmentEssence(
        tone_tags=tone_tags,
        dialogue_density=round(dialogue_density, 4),
        introspection_level=introspection_score,
        mystery_level=mystery_score,
        descriptors=descriptors,
        generation_guidance=guidance,
    )


def _build_character_profiles(
    *,
    segment_texts: dict[str, str],
    entities: list[EntityMention],
) -> list[CharacterEssenceProfile]:
    profiles: list[CharacterEssenceProfile] = []
    for entity in sorted(entities, key=lambda item: item.name):
        if entity.entity_type != "character":
            continue
        evidence_ids = [
            segment_id for segment_id in entity.segment_ids if segment_id in segment_texts
        ]
        if not evidence_ids:
            continue
        segment_tokens: dict[str, list[str]] = {
            segment_id: _tokenize(segment_texts[segment_id]) for segment_id in evidence_ids
        }
        aggregate_tokens = [token for tokens in segment_tokens.values() for token in tokens]
        trait_scores = {
            trait: _keyword_score(tokens=aggregate_tokens, keywords=lexicon)
            for trait, lexicon in _CHARACTER_TRAIT_LEXICONS.items()
        }
        ordered_traits = sorted(
            trait_scores.items(), key=lambda pair: (pair[1], pair[0]), reverse=True
        )
        selected_traits = [trait for trait, score in ordered_traits if score >= 0.18][:3]
        if not selected_traits:
            selected_traits = [ordered_traits[0][0] if ordered_traits else "steady"]

        dominant_traits: list[str] = []
        for tokens in segment_tokens.values():
            by_trait = {
                trait: _keyword_score(tokens=tokens, keywords=lexicon)
                for trait, lexicon in _CHARACTER_TRAIT_LEXICONS.items()
            }
            ranked = sorted(by_trait.items(), key=lambda pair: (pair[1], pair[0]), reverse=True)
            dominant_traits.append(ranked[0][0] if ranked and ranked[0][1] > 0 else "neutral")
        dominant_counts = Counter(dominant_traits)
        consistency = round(max(dominant_counts.values()) / max(len(dominant_traits), 1), 4)
        profiles.append(
            CharacterEssenceProfile(
                character_name=entity.name,
                essence_traits=selected_traits,
                consistency_score=consistency,
                evidence_segment_ids=evidence_ids,
            )
        )
    return profiles


def _build_world_essence(*, texts: list[str]) -> WorldEssenceProfile:
    tokens = _tokenize_texts(texts)
    magic_level = _keyword_score(tokens=tokens, keywords=_MAGIC_KEYWORDS)
    tech_level = _keyword_score(tokens=tokens, keywords=_TECH_KEYWORDS)
    culture_density = _keyword_score(tokens=tokens, keywords=_CULTURE_KEYWORDS)
    mystery_level = _keyword_score(tokens=tokens, keywords=_MYSTERY_KEYWORDS)
    descriptors = [
        f"{_level_prefix(magic_level)}-magic",
        f"{_level_prefix(tech_level)}-tech",
        f"{_level_prefix(culture_density)}-culture",
        ("mysterious" if mystery_level >= 0.33 else "transparent"),
    ]
    return WorldEssenceProfile(
        magic_level=magic_level,
        tech_level=tech_level,
        culture_density=culture_density,
        mystery_level=mystery_level,
        descriptors=descriptors,
    )


def _build_world_evolution(*, texts: list[str]) -> list[WorldStageSnapshot]:
    if not texts:
        return []
    buckets: dict[str, list[str]] = {stage: [] for stage in STORY_STAGE_ORDER}
    total = len(texts)
    for index, text in enumerate(texts):
        stage_index = min(3, math.floor((index * 4) / max(total, 1)))
        stage = STORY_STAGE_ORDER[stage_index]
        buckets[stage].append(text)
    snapshots: list[WorldStageSnapshot] = []
    for stage in STORY_STAGE_ORDER:
        world = _build_world_essence(texts=buckets[stage])
        snapshots.append(
            WorldStageSnapshot(
                stage=stage,
                magic_level=world.magic_level,
                tech_level=world.tech_level,
                culture_density=world.culture_density,
                mystery_level=world.mystery_level,
                descriptor=", ".join(world.descriptors),
            )
        )
    return snapshots


def _score_event_world_alignment(
    *,
    events: list[ExtractedEvent],
    world: WorldEssenceProfile,
) -> float:
    if not events:
        return 0.0
    scores: list[float] = []
    for event in events:
        tokens = _tokenize(event.summary)
        event_magic = _keyword_score(tokens=tokens, keywords=_MAGIC_KEYWORDS)
        event_tech = _keyword_score(tokens=tokens, keywords=_TECH_KEYWORDS)
        event_culture = _keyword_score(tokens=tokens, keywords=_CULTURE_KEYWORDS)
        event_mystery = _keyword_score(tokens=tokens, keywords=_MYSTERY_KEYWORDS)
        score = (
            (1.0 - abs(event_magic - world.magic_level))
            + (1.0 - abs(event_tech - world.tech_level))
            + (1.0 - abs(event_culture - world.culture_density))
            + (1.0 - abs(event_mystery - world.mystery_level))
        ) / 4
        scores.append(score)
    return round(sum(scores) / len(scores), 4)


def _introspection_score(*, texts: list[str]) -> float:
    if not texts:
        return 0.0
    matches = 0
    for text in texts:
        if _FIRST_PERSON_PATTERN.search(text) or _THOUGHT_VERB_PATTERN.search(text):
            matches += 1
    return round(matches / len(texts), 4)


def _level_prefix(score: float) -> str:
    if score >= 0.66:
        return "high"
    if score <= 0.33:
        return "low"
    return "balanced"


def _keyword_score(*, tokens: list[str], keywords: set[str]) -> float:
    if not tokens:
        return 0.0
    hits = sum(1 for token in tokens if token in keywords)
    denominator = max(1, len(tokens) // 6)
    return round(min(1.0, hits / denominator), 4)


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in _WORD_PATTERN.findall(text)]


def _tokenize_texts(texts: list[str]) -> list[str]:
    tokens: list[str] = []
    for text in texts:
        tokens.extend(_tokenize(text))
    return tokens
