"""Deterministic dialogue and narrative-detail extraction helpers."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Literal

from story_gen.core.story_schema import RawSegment

NarrativeMode = Literal["dialogue", "action", "exposition", "monologue"]

_WORD_PATTERN = re.compile(r"[A-Za-z']+")
_TRANSCRIPT_LINE = re.compile(r"^\s*(?P<speaker>[A-Z][A-Za-z0-9_. -]{0,40}):\s*(?P<utterance>.+)$")
_QUOTED_UTTERANCE = re.compile(r'"(?P<utterance>[^"\n]{1,800})"')
_SPEAKER_BEFORE_QUOTE = re.compile(
    r"(?P<speaker>[A-Z][A-Za-z0-9_-]{1,40})[^.!?\n]{0,90}\b(?:said|asked|whispered|"
    r"replied|murmured|shouted|cried|yelled|told|answered)\s*$",
    flags=re.IGNORECASE,
)
_SPEAKER_AFTER_QUOTE = re.compile(
    r"^\s*[,;-]?\s*(?:said|asked|whispered|replied|murmured|shouted|cried|yelled|"
    r"told|answered)\s+(?P<speaker>[A-Z][A-Za-z0-9_-]{1,40})",
    flags=re.IGNORECASE,
)
_FIRST_PERSON_PATTERN = re.compile(r"\b(i|me|my|mine|myself)\b", flags=re.IGNORECASE)
_THOUGHT_VERB_PATTERN = re.compile(
    r"\b(think|thought|wonder|wondered|remember|remembered|realize|realized|"
    r"wish|wished|fear|feared|hope|hoped|decide|decided)\b",
    flags=re.IGNORECASE,
)
_ACTION_KEYWORDS = {
    "run",
    "ran",
    "rush",
    "rushed",
    "fight",
    "fought",
    "grab",
    "grabbed",
    "strike",
    "struck",
    "attack",
    "attacked",
    "chase",
    "chased",
    "jump",
    "jumped",
    "climb",
    "climbed",
    "confront",
    "confronts",
    "confronted",
    "escape",
    "escaped",
    "sprint",
    "sprinted",
}
_EXPOSITION_KEYWORDS = {
    "because",
    "therefore",
    "history",
    "tradition",
    "explains",
    "explained",
    "describes",
    "described",
    "had",
    "was",
    "were",
    "known",
    "believed",
    "context",
    "background",
}


@dataclass(frozen=True)
class DialogueTurn:
    """One extracted dialogue turn with heuristic speaker attribution."""

    segment_id: str
    speaker: str
    utterance: str
    attribution_method: str


@dataclass(frozen=True)
class InternalMonologueSignal:
    """One internal-thought signal discovered in a segment."""

    segment_id: str
    excerpt: str
    confidence: float


@dataclass(frozen=True)
class NarrativeBalance:
    """Aggregate narrative-mode ratios across analyzed segments."""

    dialogue_ratio: float
    action_ratio: float
    exposition_ratio: float
    monologue_ratio: float


@dataclass(frozen=True)
class DialogueExtractionDetails:
    """Combined extraction details used by dashboard and diagnostics surfaces."""

    segment_ids: list[str]
    dialogue_turns: list[DialogueTurn]
    internal_monologues: list[InternalMonologueSignal]
    dominant_mode_by_segment: dict[str, NarrativeMode]
    narrative_balance: NarrativeBalance


def extract_dialogue_details(
    *,
    segments: list[RawSegment],
    known_character_names: list[str] | None = None,
) -> DialogueExtractionDetails:
    """Extract dialogue turns, internal monologue, and narrative mode balance."""
    known_names = {name.strip().lower() for name in (known_character_names or []) if name.strip()}
    segment_ids: list[str] = []
    dialogue_turns: list[DialogueTurn] = []
    internal_monologues: list[InternalMonologueSignal] = []
    mode_by_segment: dict[str, NarrativeMode] = {}
    mode_counts: Counter[NarrativeMode] = Counter()

    for segment in segments:
        text = (segment.translated_text or segment.normalized_text).strip()
        if not text:
            continue
        segment_ids.append(segment.segment_id)

        turns = _extract_turns(segment_id=segment.segment_id, text=text, known_names=known_names)
        dialogue_turns.extend(turns)
        monologue = _extract_internal_monologue(segment_id=segment.segment_id, text=text)
        if monologue is not None:
            internal_monologues.append(monologue)
        dominant_mode = _dominant_mode(text=text, turns=turns, has_monologue=monologue is not None)
        mode_by_segment[segment.segment_id] = dominant_mode
        mode_counts[dominant_mode] += 1

    total = max(len(segment_ids), 1)
    details = DialogueExtractionDetails(
        segment_ids=segment_ids,
        dialogue_turns=dialogue_turns,
        internal_monologues=internal_monologues,
        dominant_mode_by_segment=mode_by_segment,
        narrative_balance=NarrativeBalance(
            dialogue_ratio=round(mode_counts["dialogue"] / total, 4),
            action_ratio=round(mode_counts["action"] / total, 4),
            exposition_ratio=round(mode_counts["exposition"] / total, 4),
            monologue_ratio=round(mode_counts["monologue"] / total, 4),
        ),
    )
    return details


def _extract_turns(
    *,
    segment_id: str,
    text: str,
    known_names: set[str],
) -> list[DialogueTurn]:
    transcript_match = _TRANSCRIPT_LINE.match(text)
    if transcript_match:
        speaker = _normalize_speaker(transcript_match.group("speaker"), known_names=known_names)
        utterance = (transcript_match.group("utterance") or "").strip()
        if utterance:
            return [
                DialogueTurn(
                    segment_id=segment_id,
                    speaker=speaker,
                    utterance=utterance,
                    attribution_method="transcript_prefix",
                )
            ]

    turns: list[DialogueTurn] = []
    for match in _QUOTED_UTTERANCE.finditer(text):
        utterance = (match.group("utterance") or "").strip()
        if not utterance:
            continue
        prefix = text[: match.start()]
        suffix = text[match.end() :]
        speaker, method = _resolve_speaker(prefix=prefix, suffix=suffix, known_names=known_names)
        turns.append(
            DialogueTurn(
                segment_id=segment_id,
                speaker=speaker,
                utterance=utterance,
                attribution_method=method,
            )
        )
    return turns


def _resolve_speaker(
    *,
    prefix: str,
    suffix: str,
    known_names: set[str],
) -> tuple[str, str]:
    before_match = _SPEAKER_BEFORE_QUOTE.search(prefix)
    if before_match:
        speaker = _normalize_speaker(before_match.group("speaker"), known_names=known_names)
        return speaker, "narrative_before_quote"

    after_match = _SPEAKER_AFTER_QUOTE.search(suffix)
    if after_match:
        speaker = _normalize_speaker(after_match.group("speaker"), known_names=known_names)
        return speaker, "narrative_after_quote"

    return "unknown", "unknown"


def _normalize_speaker(raw: str | None, *, known_names: set[str]) -> str:
    value = (raw or "").strip().lower()
    if not value:
        return "unknown"
    if known_names and value not in known_names:
        return "unknown"
    return value


def _extract_internal_monologue(*, segment_id: str, text: str) -> InternalMonologueSignal | None:
    has_first_person = bool(_FIRST_PERSON_PATTERN.search(text))
    has_thought_verb = bool(_THOUGHT_VERB_PATTERN.search(text))
    if not has_first_person and not has_thought_verb:
        return None
    confidence = 0.45
    if has_first_person:
        confidence += 0.25
    if has_thought_verb:
        confidence += 0.25
    if "?" in text:
        confidence += 0.05
    excerpt = text.strip()
    if len(excerpt) > 140:
        excerpt = f"{excerpt[:137]}..."
    return InternalMonologueSignal(
        segment_id=segment_id,
        excerpt=excerpt,
        confidence=round(min(confidence, 0.95), 3),
    )


def _dominant_mode(
    *,
    text: str,
    turns: list[DialogueTurn],
    has_monologue: bool,
) -> NarrativeMode:
    tokens = [token.lower() for token in _WORD_PATTERN.findall(text)]
    token_total = max(len(tokens), 1)
    action_hits = sum(1 for token in tokens if token in _ACTION_KEYWORDS)
    exposition_hits = sum(1 for token in tokens if token in _EXPOSITION_KEYWORDS)

    scores: dict[NarrativeMode, float] = {
        "dialogue": 0.0,
        "action": action_hits / token_total,
        "exposition": 0.1 + (exposition_hits / token_total),
        "monologue": 0.0,
    }
    if turns:
        scores["dialogue"] = 1.0 + min(0.6, len(turns) * 0.2)
    if has_monologue:
        scores["monologue"] = 1.05

    precedence: list[NarrativeMode] = ["monologue", "dialogue", "action", "exposition"]
    return max(precedence, key=lambda mode: (scores[mode], -precedence.index(mode)))
