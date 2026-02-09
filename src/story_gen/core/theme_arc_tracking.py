"""Theme, character arc, conflict, and emotion tracking across stages."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Literal

from story_gen.core.pipeline_contracts import validate_theme_input, validate_theme_output
from story_gen.core.story_schema import (
    STORY_STAGE_ORDER,
    ConfidenceScore,
    EntityMention,
    ProvenanceRecord,
    StoryBeat,
    StoryStage,
    ThemeSignal,
    stable_id,
)

_TOKEN_RE = re.compile(r"[a-z']+")

# Evidence-driven weighted cue map by theme.
_THEME_LEXICON: dict[str, dict[str, float]] = {
    "memory": {
        "memory": 1.0,
        "remember": 0.9,
        "archive": 0.8,
        "history": 0.8,
        "record": 0.7,
        "ledger": 0.7,
    },
    "conflict": {
        "conflict": 1.0,
        "fight": 0.9,
        "war": 1.0,
        "battle": 0.9,
        "denies": 0.7,
        "betray": 0.9,
        "anger": 0.7,
    },
    "identity": {
        "identity": 1.0,
        "self": 0.8,
        "name": 0.7,
        "origin": 0.8,
        "truth": 0.7,
    },
    "trust": {
        "trust": 1.0,
        "loyal": 0.8,
        "truth": 0.8,
        "heal": 0.7,
        "accepts": 0.7,
        "resolve": 0.7,
    },
}

_CONFLICT_CUES: dict[str, float] = {
    "conflict": 1.0,
    "fight": 0.9,
    "war": 1.0,
    "battle": 0.9,
    "betray": 0.9,
    "denies": 0.8,
    "anger": 0.6,
    "loss": 0.7,
}
_RESOLUTION_CUES: dict[str, float] = {
    "heal": 0.9,
    "accepts": 0.8,
    "trust": 0.8,
    "truth": 0.5,
    "resolved": 0.8,
    "peace": 1.0,
}
_POSITIVE_CUES: dict[str, float] = {
    "hope": 1.0,
    "trust": 0.8,
    "healed": 1.0,
    "heal": 0.9,
    "resolved": 0.9,
    "love": 0.9,
    "calm": 0.8,
    "accepts": 0.8,
}
_NEGATIVE_CUES: dict[str, float] = {
    "fear": 0.9,
    "betray": 0.9,
    "war": 1.0,
    "loss": 0.9,
    "anger": 0.8,
    "conflict": 1.0,
    "denies": 0.8,
}
ThemeDirection = Literal["emerging", "strengthening", "steady", "fading"]


@dataclass(frozen=True)
class ArcSignal:
    """Character arc signal used by dashboard arc charts."""

    entity_id: str
    entity_name: str
    stage: StoryStage
    state: str
    delta: float
    evidence_segment_ids: tuple[str, ...] = ()
    confidence: float = 0.0


@dataclass(frozen=True)
class ConflictShift:
    """Conflict shift signal used by dashboard read model."""

    stage: StoryStage
    from_state: StoryStage
    to_state: StoryStage
    intensity_delta: float
    evidence_segment_ids: tuple[str, ...] = ()
    confidence: float = 0.0


@dataclass(frozen=True)
class EmotionSignal:
    """Emotion signal per stage."""

    stage: StoryStage
    tone: str
    score: float
    evidence_segment_ids: tuple[str, ...] = ()
    confidence: float = 0.0


@dataclass(frozen=True)
class _StageContext:
    stage: StoryStage
    beats: tuple[StoryBeat, ...]
    evidence_segment_ids: tuple[str, ...]
    token_counts: Counter[str]


def track_theme_arc_signals(
    *,
    beats: list[StoryBeat],
    entities: list[EntityMention],
) -> tuple[list[ThemeSignal], list[ArcSignal], list[ConflictShift], list[EmotionSignal]]:
    """Generate stage-aware trend signals for dashboard and insights."""
    validate_theme_input(beats)
    contexts = _build_stage_contexts(beats)
    themes = _detect_themes(contexts)
    validate_theme_output(themes)
    arcs = _build_arcs(contexts, entities)
    conflicts = _build_conflicts(contexts)
    emotions = _build_emotions(contexts)
    return themes, arcs, conflicts, emotions


def _build_stage_contexts(beats: list[StoryBeat]) -> dict[StoryStage, _StageContext]:
    stage_beats: dict[StoryStage, list[StoryBeat]] = {stage: [] for stage in STORY_STAGE_ORDER}
    for beat in beats:
        stage_beats[beat.stage].append(beat)

    contexts: dict[StoryStage, _StageContext] = {}
    for stage in STORY_STAGE_ORDER:
        ordered_beats = tuple(sorted(stage_beats[stage], key=lambda beat: beat.order_index))
        evidence_ids: list[str] = []
        for beat in ordered_beats:
            for segment_id in beat.evidence_segment_ids:
                if segment_id not in evidence_ids:
                    evidence_ids.append(segment_id)
        tokens = Counter(_tokenize(" ".join(beat.summary.lower() for beat in ordered_beats)))
        contexts[stage] = _StageContext(
            stage=stage,
            beats=ordered_beats,
            evidence_segment_ids=tuple(evidence_ids),
            token_counts=tokens,
        )
    return contexts


def _detect_themes(contexts: dict[StoryStage, _StageContext]) -> list[ThemeSignal]:
    signals: list[ThemeSignal] = []
    any_theme_emitted = False

    for theme_label in sorted(_THEME_LEXICON):
        previous_strength = 0.0
        theme_started = False
        lexicon = _THEME_LEXICON[theme_label]
        for stage in STORY_STAGE_ORDER:
            context = contexts[stage]
            if not context.evidence_segment_ids:
                continue

            weighted_hits = _weighted_count(context.token_counts, lexicon)
            max_score = max(1.0, len(context.beats) * 2.8)
            strength = round(min(1.0, weighted_hits / max_score), 3)
            if strength <= 0.0 and not theme_started:
                continue

            direction = _trend_direction(previous_strength=previous_strength, current=strength)
            confidence = _bounded(
                0.42
                + min(0.3, weighted_hits * 0.11)
                + min(0.18, len(context.evidence_segment_ids) * 0.03)
                + min(0.1, len(context.beats) * 0.04)
            )
            signals.append(
                ThemeSignal(
                    theme_id=stable_id(
                        prefix="theme",
                        text=f"{theme_label}:{stage}:{strength}:{','.join(context.evidence_segment_ids)}",
                    ),
                    label=theme_label,
                    stage=stage,
                    strength=strength,
                    direction=direction,
                    evidence_segment_ids=list(context.evidence_segment_ids),
                    confidence=ConfidenceScore(method="theme.trend.v2", score=confidence),
                    provenance=ProvenanceRecord(
                        source_segment_ids=list(context.evidence_segment_ids),
                        generator="theme_tracker_v2",
                    ),
                )
            )
            previous_strength = strength
            theme_started = True

        any_theme_emitted = any_theme_emitted or theme_started

    if not any_theme_emitted:
        for stage in STORY_STAGE_ORDER:
            context = contexts[stage]
            if not context.evidence_segment_ids:
                continue
            signals.append(
                ThemeSignal(
                    theme_id=stable_id(prefix="theme", text=f"story:{stage}"),
                    label="story",
                    stage=stage,
                    strength=0.5,
                    direction="emerging" if stage == STORY_STAGE_ORDER[0] else "steady",
                    evidence_segment_ids=list(context.evidence_segment_ids),
                    confidence=ConfidenceScore(method="theme.trend.v2", score=0.55),
                    provenance=ProvenanceRecord(
                        source_segment_ids=list(context.evidence_segment_ids),
                        generator="theme_tracker_v2",
                    ),
                )
            )
            break
    stage_index = {stage: index for index, stage in enumerate(STORY_STAGE_ORDER)}
    return sorted(
        signals, key=lambda signal: (stage_index[signal.stage], signal.label, signal.theme_id)
    )


def _build_arcs(
    contexts: dict[StoryStage, _StageContext],
    entities: list[EntityMention],
) -> list[ArcSignal]:
    if not entities:
        return []
    ordered = sorted(entities, key=lambda entity: entity.name)
    arcs: list[ArcSignal] = []
    for entity in ordered:
        entity_segments = set(entity.segment_ids)
        prev = 0.0
        for stage in STORY_STAGE_ORDER:
            context = contexts[stage]
            if not context.evidence_segment_ids:
                continue
            overlap = [seg for seg in context.evidence_segment_ids if seg in entity_segments]
            stage_value = round(len(overlap) / max(len(context.evidence_segment_ids), 1), 3)
            delta = round(stage_value - prev, 3)
            state = _arc_state(previous=prev, current=stage_value)
            confidence = _bounded(
                0.35
                + min(0.25, len(context.evidence_segment_ids) * 0.04)
                + min(0.35, len(overlap) * 0.2)
            )
            evidence = tuple(overlap) if overlap else context.evidence_segment_ids[:1]
            arcs.append(
                ArcSignal(
                    entity_id=entity.entity_id,
                    entity_name=entity.name,
                    stage=stage,
                    state=state,
                    delta=delta,
                    evidence_segment_ids=evidence,
                    confidence=confidence,
                )
            )
            prev = stage_value
    return arcs


def _build_conflicts(contexts: dict[StoryStage, _StageContext]) -> list[ConflictShift]:
    stage_scores: dict[StoryStage, float] = {stage: 0.5 for stage in STORY_STAGE_ORDER}
    stage_confidence: dict[StoryStage, float] = {stage: 0.45 for stage in STORY_STAGE_ORDER}
    fallback_evidence = next(
        (
            context.evidence_segment_ids
            for context in contexts.values()
            if context.evidence_segment_ids
        ),
        (),
    )
    for stage in STORY_STAGE_ORDER:
        context = contexts[stage]
        if not context.evidence_segment_ids:
            continue
        conflict_weight = _weighted_count(context.token_counts, _CONFLICT_CUES)
        resolution_weight = _weighted_count(context.token_counts, _RESOLUTION_CUES)
        raw = conflict_weight - (0.65 * resolution_weight)
        stage_scores[stage] = _bounded(0.5 + (raw / 4.0))
        stage_confidence[stage] = _bounded(
            0.4 + min(0.25, len(context.evidence_segment_ids) * 0.04) + min(0.25, abs(raw) * 0.12)
        )

    shifts: list[ConflictShift] = []
    for idx in range(1, len(STORY_STAGE_ORDER)):
        prev_stage = STORY_STAGE_ORDER[idx - 1]
        stage = STORY_STAGE_ORDER[idx]
        delta = round(stage_scores[stage] - stage_scores[prev_stage], 3)
        context = contexts[stage]
        evidence = (
            context.evidence_segment_ids
            if context.evidence_segment_ids
            else contexts[prev_stage].evidence_segment_ids
            if contexts[prev_stage].evidence_segment_ids
            else fallback_evidence
        )
        shifts.append(
            ConflictShift(
                stage=stage,
                from_state=prev_stage,
                to_state=stage,
                intensity_delta=delta,
                evidence_segment_ids=evidence,
                confidence=stage_confidence[stage],
            )
        )
    return shifts


def _build_emotions(contexts: dict[StoryStage, _StageContext]) -> list[EmotionSignal]:
    signals: list[EmotionSignal] = []
    for stage in STORY_STAGE_ORDER:
        context = contexts[stage]
        if not context.evidence_segment_ids:
            continue
        positive = _weighted_count(context.token_counts, _POSITIVE_CUES)
        negative = _weighted_count(context.token_counts, _NEGATIVE_CUES)
        score = round((positive + 1.0) / (positive + negative + 2.0), 3)
        tone = "positive" if score >= 0.58 else "negative" if score <= 0.42 else "neutral"
        confidence = _bounded(
            0.4
            + min(0.25, len(context.evidence_segment_ids) * 0.04)
            + min(0.3, (positive + negative) * 0.1)
        )
        signals.append(
            EmotionSignal(
                stage=stage,
                tone=tone,
                score=score,
                evidence_segment_ids=context.evidence_segment_ids,
                confidence=confidence,
            )
        )
    return signals


def _tokenize(text: str) -> list[str]:
    return [token for token in _TOKEN_RE.findall(text.lower()) if token]


def _weighted_count(token_counts: Counter[str], weights: dict[str, float]) -> float:
    total = 0.0
    for token, weight in weights.items():
        total += token_counts.get(token, 0) * weight
    return total


def _trend_direction(*, previous_strength: float, current: float) -> ThemeDirection:
    if previous_strength <= 0.01 and current > 0.01:
        return "emerging"
    if current > previous_strength + 0.08:
        return "strengthening"
    if current < previous_strength - 0.08:
        return "fading"
    return "steady"


def _arc_state(*, previous: float, current: float) -> str:
    if previous <= 0.05 and current > 0.05:
        return "emerging"
    if current > previous + 0.08:
        return "strengthening"
    if current < previous - 0.08:
        return "fading"
    if current <= 0.05:
        return "inactive"
    return "steady"


def _bounded(value: float) -> float:
    return round(min(0.98, max(0.0, value)), 3)
