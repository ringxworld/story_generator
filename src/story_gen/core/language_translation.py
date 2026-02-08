"""Language detection and deterministic translation helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from story_gen.core.story_schema import RawSegment

_SPANISH_MARKERS: Final[set[str]] = {
    "el",
    "la",
    "los",
    "las",
    "que",
    "una",
    "pero",
    "porque",
    "historia",
    "cuando",
}
_FRENCH_MARKERS: Final[set[str]] = {
    "le",
    "la",
    "les",
    "une",
    "des",
    "dans",
    "avec",
    "histoire",
    "quand",
    "pourquoi",
}

_SPANISH_TO_ENGLISH: Final[dict[str, str]] = {
    # TODO(#1002): Replace toy token map with model-backed translation service.
    "historia": "story",
    "familia": "family",
    "conflicto": "conflict",
    "amor": "love",
    "guerra": "war",
    "memoria": "memory",
}
_FRENCH_TO_ENGLISH: Final[dict[str, str]] = {
    "histoire": "story",
    "famille": "family",
    "conflit": "conflict",
    "amour": "love",
    "guerre": "war",
    "memoire": "memory",
}
_JAPANESE_SCRIPT = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff]")
_LATIN_LETTER = re.compile(r"[A-Za-z]")


@dataclass(frozen=True)
class LanguageDetectionResult:
    """Language metadata for one segment or document."""

    language_code: str
    confidence: float
    detector_version: str = "heuristic.v1"


@dataclass(frozen=True)
class SegmentAlignment:
    """Basic segment alignment metadata between source and translation."""

    source_segment_id: str
    source_offsets: tuple[int, int]
    target_offsets: tuple[int, int]
    method: str
    quality_score: float


def detect_language(text: str) -> LanguageDetectionResult:
    """Detect language from lightweight lexical markers."""
    # TODO(#1003): Upgrade from lexical/script heuristics to a robust language-id model.
    japanese_chars = len(_JAPANESE_SCRIPT.findall(text))
    latin_chars = len(_LATIN_LETTER.findall(text))
    if japanese_chars >= 4 and japanese_chars >= latin_chars:
        confidence = min(1.0, 0.8 + japanese_chars / max(len(text), 1) * 0.2)
        return LanguageDetectionResult(language_code="ja", confidence=round(confidence, 3))

    tokens = [token.strip(".,!?;:()[]{}\"'").lower() for token in text.split()]
    if not tokens:
        return LanguageDetectionResult(language_code="und", confidence=0.0)

    spanish_hits = sum(1 for token in tokens if token in _SPANISH_MARKERS)
    french_hits = sum(1 for token in tokens if token in _FRENCH_MARKERS)
    total = max(len(tokens), 1)
    if spanish_hits > french_hits and spanish_hits > 0:
        return LanguageDetectionResult(
            language_code="es", confidence=min(1.0, spanish_hits / total + 0.2)
        )
    if french_hits > spanish_hits and french_hits > 0:
        return LanguageDetectionResult(
            language_code="fr", confidence=min(1.0, french_hits / total + 0.2)
        )
    return LanguageDetectionResult(language_code="en", confidence=0.65)


def _replace_tokens(text: str, replacements: dict[str, str]) -> str:
    words = text.split()
    translated: list[str] = []
    for word in words:
        cleaned = word.strip(".,!?;:()[]{}\"'").lower()
        translated_word = replacements.get(cleaned)
        translated.append(translated_word if translated_word is not None else word)
    return " ".join(translated)


def translate_segments(
    *,
    segments: list[RawSegment],
    target_language: str = "en",
) -> tuple[list[RawSegment], list[SegmentAlignment], str]:
    """Detect and translate segments into target language when needed."""
    # TODO(#1004): Add external translation provider path with retries and circuit-breakers.
    translated_segments: list[RawSegment] = []
    alignments: list[SegmentAlignment] = []
    detected_languages: list[str] = []

    for segment in segments:
        detected = detect_language(segment.normalized_text)
        detected_languages.append(detected.language_code)
        translated_text = segment.normalized_text
        quality_score = 1.0
        if target_language == "en" and detected.language_code == "es":
            translated_text = _replace_tokens(segment.normalized_text, _SPANISH_TO_ENGLISH)
            quality_score = 0.8
        elif target_language == "en" and detected.language_code == "fr":
            translated_text = _replace_tokens(segment.normalized_text, _FRENCH_TO_ENGLISH)
            quality_score = 0.8

        translated_segment = segment.model_copy(
            update={
                "language_code": detected.language_code,
                "translated_text": translated_text,
            }
        )
        translated_segments.append(translated_segment)
        alignments.append(
            SegmentAlignment(
                source_segment_id=segment.segment_id,
                source_offsets=(0, len(segment.normalized_text)),
                target_offsets=(0, len(translated_text)),
                method="token_replace.v1",
                quality_score=quality_score,
            )
        )

    source_language = _majority_language(detected_languages)
    return translated_segments, alignments, source_language


def _majority_language(values: list[str]) -> str:
    if not values:
        return "und"
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    ordered = sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))
    return ordered[0][0]
