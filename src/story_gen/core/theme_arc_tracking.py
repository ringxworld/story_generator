"""Theme, character arc, conflict, and emotion tracking across stages."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Literal

from story_gen.core.pipeline_contracts import validate_theme_input, validate_theme_output
from story_gen.core.story_schema import (
    ConfidenceScore,
    EntityMention,
    ProvenanceRecord,
    StoryBeat,
    ThemeSignal,
    stable_id,
)

_THEME_KEYWORDS: dict[str, tuple[str, ...]] = {
    "memory": ("memory", "remember", "archive", "history"),
    "conflict": ("fight", "conflict", "war", "battle"),
    "identity": ("identity", "name", "self", "origin"),
    "trust": ("trust", "betray", "truth", "loyal"),
}

_POSITIVE_WORDS = {"hope", "trust", "healed", "resolved", "love", "calm"}
_NEGATIVE_WORDS = {"fear", "betray", "war", "loss", "anger", "conflict"}
ThemeDirection = Literal["emerging", "strengthening", "steady", "fading"]


@dataclass(frozen=True)
class ArcSignal:
    """Character arc signal used by dashboard arc charts."""

    entity_id: str
    entity_name: str
    stage: str
    state: str
    delta: float


@dataclass(frozen=True)
class ConflictShift:
    """Conflict shift signal used by dashboard read model."""

    stage: str
    from_state: str
    to_state: str
    intensity_delta: float


@dataclass(frozen=True)
class EmotionSignal:
    """Emotion signal per stage."""

    stage: str
    tone: str
    score: float


def track_theme_arc_signals(
    *,
    beats: list[StoryBeat],
    entities: list[EntityMention],
) -> tuple[list[ThemeSignal], list[ArcSignal], list[ConflictShift], list[EmotionSignal]]:
    """Generate stage-aware trend signals for dashboard and insights."""
    validate_theme_input(beats)
    themes = _detect_themes(beats)
    validate_theme_output(themes)
    arcs = _build_arcs(beats, entities)
    conflicts = _build_conflicts(beats)
    emotions = _build_emotions(beats)
    return themes, arcs, conflicts, emotions


def _detect_themes(beats: list[StoryBeat]) -> list[ThemeSignal]:
    by_theme: dict[str, list[tuple[int, StoryBeat]]] = {}
    for beat in beats:
        text = beat.summary.lower()
        for theme, keywords in _THEME_KEYWORDS.items():
            if any(keyword in text for keyword in keywords):
                by_theme.setdefault(theme, []).append((beat.order_index, beat))

    if not by_theme:
        by_theme["story"] = [(beat.order_index, beat) for beat in beats[:1]]

    signals: list[ThemeSignal] = []
    for theme in sorted(by_theme):
        sorted_hits = sorted(by_theme[theme], key=lambda pair: pair[0])
        max_hits = max(len(sorted_hits), 1)
        for position, (_, beat) in enumerate(sorted_hits, start=1):
            strength = round(position / max_hits, 3)
            direction: ThemeDirection
            if position == 1:
                direction = "emerging"
            elif position == max_hits:
                direction = "strengthening"
            else:
                direction = "steady"
            signals.append(
                ThemeSignal(
                    theme_id=stable_id(prefix="theme", text=f"{theme}:{beat.stage}:{position}"),
                    label=theme,
                    stage=beat.stage,
                    strength=strength,
                    direction=direction,
                    evidence_segment_ids=beat.evidence_segment_ids,
                    confidence=ConfidenceScore(method="theme.rule.v1", score=0.66),
                    provenance=ProvenanceRecord(
                        source_segment_ids=beat.evidence_segment_ids,
                        generator="theme_tracker",
                    ),
                )
            )
    return sorted(signals, key=lambda signal: (signal.stage, signal.theme_id))


def _build_arcs(beats: list[StoryBeat], entities: list[EntityMention]) -> list[ArcSignal]:
    if not entities:
        return []
    stage_counter = Counter(beat.stage for beat in beats)
    ordered = sorted(entities, key=lambda entity: entity.name)
    arcs: list[ArcSignal] = []
    for entity in ordered:
        prev = 0.0
        for stage in ("setup", "escalation", "climax", "resolution"):
            stage_value = stage_counter.get(stage, 0) / max(len(beats), 1)
            delta = round(stage_value - prev, 3)
            state = "active" if stage_value > 0 else "inactive"
            arcs.append(
                ArcSignal(
                    entity_id=entity.entity_id,
                    entity_name=entity.name,
                    stage=stage,
                    state=state,
                    delta=delta,
                )
            )
            prev = stage_value
    return arcs


def _build_conflicts(beats: list[StoryBeat]) -> list[ConflictShift]:
    stage_scores: dict[str, float] = {}
    for stage in ("setup", "escalation", "climax", "resolution"):
        stage_text = " ".join(beat.summary.lower() for beat in beats if beat.stage == stage)
        score = sum(1 for token in _NEGATIVE_WORDS if token in stage_text)
        stage_scores[stage] = float(score)

    shifts: list[ConflictShift] = []
    ordered_stages = ("setup", "escalation", "climax", "resolution")
    for idx in range(1, len(ordered_stages)):
        prev_stage = ordered_stages[idx - 1]
        stage = ordered_stages[idx]
        delta = round(stage_scores[stage] - stage_scores[prev_stage], 3)
        shifts.append(
            ConflictShift(
                stage=stage,
                from_state=prev_stage,
                to_state=stage,
                intensity_delta=delta,
            )
        )
    return shifts


def _build_emotions(beats: list[StoryBeat]) -> list[EmotionSignal]:
    signals: list[EmotionSignal] = []
    for stage in ("setup", "escalation", "climax", "resolution"):
        stage_text = " ".join(beat.summary.lower() for beat in beats if beat.stage == stage)
        positive = sum(1 for token in _POSITIVE_WORDS if token in stage_text)
        negative = sum(1 for token in _NEGATIVE_WORDS if token in stage_text)
        score = 0.5
        if positive + negative > 0:
            score = round((positive + 1) / (positive + negative + 2), 3)
        tone = "positive" if score >= 0.55 else "negative" if score <= 0.45 else "neutral"
        signals.append(EmotionSignal(stage=stage, tone=tone, score=score))
    return signals
