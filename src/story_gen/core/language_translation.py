"""Language ID and translation helpers with provider fallback semantics."""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from typing import Final, Literal

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
    "familia",
    "memoria",
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
    "famille",
    "memoire",
}
_ENGLISH_MARKERS: Final[set[str]] = {
    "the",
    "and",
    "story",
    "memory",
    "council",
    "archive",
}

_SPANISH_TO_ENGLISH: Final[dict[str, str]] = {
    "historia": "story",
    "familia": "family",
    "conflicto": "conflict",
    "amor": "love",
    "guerra": "war",
    "memoria": "memory",
    "consejo": "council",
    "archivo": "archive",
    "verdad": "truth",
}
_FRENCH_TO_ENGLISH: Final[dict[str, str]] = {
    "histoire": "story",
    "famille": "family",
    "conflit": "conflict",
    "amour": "love",
    "guerre": "war",
    "memoire": "memory",
    "conseil": "council",
    "archive": "archive",
    "verite": "truth",
}
_LANGUAGE_TO_MAP: Final[dict[str, dict[str, str]]] = {
    "es": _SPANISH_TO_ENGLISH,
    "fr": _FRENCH_TO_ENGLISH,
}
_TOKEN_RE = re.compile(r"[A-Za-z']+")
_JAPANESE_SCRIPT = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff]")
_LATIN_LETTER = re.compile(r"[A-Za-z]")


@dataclass(frozen=True)
class LanguageDetectionResult:
    """Language metadata for one segment or document."""

    language_code: str
    confidence: float
    detector_version: str = "heuristic.v2"


@dataclass(frozen=True)
class SegmentAlignment:
    """Basic segment alignment metadata between source and translation."""

    source_segment_id: str
    source_offsets: tuple[int, int]
    target_offsets: tuple[int, int]
    method: str
    quality_score: float


@dataclass(frozen=True)
class TranslationIssue:
    """Translation provider degradation event."""

    code: str
    severity: Literal["warning", "error"]
    message: str
    segment_id: str | None = None
    attempt: int | None = None


@dataclass(frozen=True)
class TranslationDiagnostics:
    """Diagnostics emitted by translation stage."""

    provider: str
    language_id_provider: str
    retry_count: int
    timeout_budget_ms: int
    circuit_breaker_failures: int
    circuit_breaker_reset_seconds: int
    fallback_used: bool
    degraded_segments: int
    issue_count: int
    issues: list[TranslationIssue]


class TranslationProviderError(RuntimeError):
    """Raised when provider-backed translation fails."""


@dataclass
class _CircuitBreakerState:
    consecutive_failures: int = 0
    open_until_monotonic: float = 0.0


_CIRCUIT_STATES: dict[str, _CircuitBreakerState] = {}


class _HeuristicLanguageIdProvider:
    name = "heuristic.v2"

    def detect(self, text: str) -> LanguageDetectionResult:
        japanese_chars = len(_JAPANESE_SCRIPT.findall(text))
        latin_chars = len(_LATIN_LETTER.findall(text))
        if japanese_chars >= 4 and japanese_chars >= latin_chars:
            confidence = min(1.0, 0.82 + japanese_chars / max(len(text), 1) * 0.18)
            return LanguageDetectionResult(language_code="ja", confidence=round(confidence, 3))

        tokens = _tokens(text)
        if not tokens:
            return LanguageDetectionResult(language_code="und", confidence=0.0)

        scores = {
            "es": _marker_score(tokens, _SPANISH_MARKERS),
            "fr": _marker_score(tokens, _FRENCH_MARKERS),
            "en": _marker_score(tokens, _ENGLISH_MARKERS),
        }
        ordered = sorted(scores.items(), key=lambda pair: (-pair[1], pair[0]))
        language, top_score = ordered[0]
        if top_score <= 0.0:
            return LanguageDetectionResult(language_code="en", confidence=0.62)
        runner_up = ordered[1][1] if len(ordered) > 1 else 0.0
        margin = max(0.0, top_score - runner_up)
        confidence = min(0.98, 0.58 + top_score * 0.22 + margin * 0.25)
        return LanguageDetectionResult(language_code=language, confidence=round(confidence, 3))


class _IdentityTranslationProvider:
    name = "identity.v1"

    def translate(self, *, text: str, source_language: str, target_language: str) -> str:
        del source_language, target_language
        return text


class _LexiconTranslationProvider:
    name = "lexicon.v2"

    def translate(self, *, text: str, source_language: str, target_language: str) -> str:
        if target_language != "en":
            return text
        replacements = _LANGUAGE_TO_MAP.get(source_language)
        if replacements is None:
            return text
        return _replace_tokens(text, replacements)


class _FailingTranslationProvider:
    name = "failing.v1"

    def translate(self, *, text: str, source_language: str, target_language: str) -> str:
        del text, source_language, target_language
        raise TranslationProviderError("Configured failing provider always raises.")


def detect_language(text: str) -> LanguageDetectionResult:
    """Detect language via configured language-ID provider."""
    provider = _resolve_language_id_provider()
    return provider.detect(text)


def translate_segments(
    *,
    segments: list[RawSegment],
    target_language: str = "en",
) -> tuple[list[RawSegment], list[SegmentAlignment], str]:
    """Translate segments into target language with fallback resilience."""
    translated, alignments, source_language, _ = translate_segments_with_diagnostics(
        segments=segments,
        target_language=target_language,
    )
    return translated, alignments, source_language


def translate_segments_with_diagnostics(
    *,
    segments: list[RawSegment],
    target_language: str = "en",
) -> tuple[list[RawSegment], list[SegmentAlignment], str, TranslationDiagnostics]:
    """Translate segments and emit diagnostics for anomaly and quality surfaces."""
    retry_count = _int_env("STORY_GEN_TRANSLATION_RETRY_COUNT", default=2, minimum=0, maximum=6)
    timeout_budget_ms = _int_env(
        "STORY_GEN_TRANSLATION_TIMEOUT_MS", default=1200, minimum=50, maximum=60000
    )
    circuit_failures = _int_env(
        "STORY_GEN_TRANSLATION_CIRCUIT_FAILURES", default=3, minimum=1, maximum=20
    )
    circuit_reset_seconds = _int_env(
        "STORY_GEN_TRANSLATION_CIRCUIT_RESET_SECONDS", default=30, minimum=1, maximum=600
    )
    provider = _resolve_translation_provider()
    language_provider = _resolve_language_id_provider()

    translated_segments: list[RawSegment] = []
    alignments: list[SegmentAlignment] = []
    detected_languages: list[str] = []
    all_issues: list[TranslationIssue] = []
    degraded_segments = 0

    for segment in segments:
        detected = language_provider.detect(segment.normalized_text)
        detected_languages.append(detected.language_code)
        translated_text, method, quality_score, issues, degraded = _translate_one_segment(
            text=segment.normalized_text,
            source_language=detected.language_code,
            target_language=target_language,
            provider=provider,
            segment_id=segment.segment_id,
            retry_count=retry_count,
            timeout_budget_ms=timeout_budget_ms,
            circuit_failures=circuit_failures,
            circuit_reset_seconds=circuit_reset_seconds,
        )
        if degraded:
            degraded_segments += 1
        all_issues.extend(issues)
        translated_segments.append(
            segment.model_copy(
                update={
                    "language_code": detected.language_code,
                    "translated_text": translated_text,
                }
            )
        )
        alignments.append(
            SegmentAlignment(
                source_segment_id=segment.segment_id,
                source_offsets=(0, len(segment.normalized_text)),
                target_offsets=(0, len(translated_text)),
                method=method,
                quality_score=quality_score,
            )
        )

    source_language = _majority_language(detected_languages)
    diagnostics = TranslationDiagnostics(
        provider=provider.name,
        language_id_provider=language_provider.name,
        retry_count=retry_count,
        timeout_budget_ms=timeout_budget_ms,
        circuit_breaker_failures=circuit_failures,
        circuit_breaker_reset_seconds=circuit_reset_seconds,
        fallback_used=degraded_segments > 0,
        degraded_segments=degraded_segments,
        issue_count=len(all_issues),
        issues=all_issues,
    )
    return translated_segments, alignments, source_language, diagnostics


def _translate_one_segment(
    *,
    text: str,
    source_language: str,
    target_language: str,
    provider: _IdentityTranslationProvider
    | _LexiconTranslationProvider
    | _FailingTranslationProvider,
    segment_id: str,
    retry_count: int,
    timeout_budget_ms: int,
    circuit_failures: int,
    circuit_reset_seconds: int,
) -> tuple[str, str, float, list[TranslationIssue], bool]:
    issues: list[TranslationIssue] = []
    if target_language != "en" or source_language in {"en", "und"}:
        return text, provider.name, 1.0, issues, False

    state = _CIRCUIT_STATES.setdefault(provider.name, _CircuitBreakerState())
    now = time.monotonic()
    if state.open_until_monotonic > now:
        fallback = _fallback_translate(text=text, source_language=source_language)
        issues.append(
            TranslationIssue(
                code="translation_provider_circuit_open",
                severity="warning",
                message=(
                    f"Translation circuit breaker is open for provider '{provider.name}', "
                    "fallback translation was used."
                ),
                segment_id=segment_id,
            )
        )
        return fallback, "fallback.lexicon.v1", _fallback_quality(fallback, text), issues, True

    for attempt in range(1, retry_count + 2):
        started = time.monotonic()
        try:
            translated = provider.translate(
                text=text,
                source_language=source_language,
                target_language=target_language,
            )
            elapsed_ms = int((time.monotonic() - started) * 1000)
            if elapsed_ms > timeout_budget_ms:
                raise TranslationProviderError(
                    f"Translation timeout exceeded budget ({elapsed_ms}ms>{timeout_budget_ms}ms)."
                )
            state.consecutive_failures = 0
            state.open_until_monotonic = 0.0
            quality = _provider_quality(
                source_text=text,
                translated_text=translated,
                source_language=source_language,
            )
            return translated, provider.name, quality, issues, False
        except Exception as exc:  # noqa: BLE001
            issues.append(
                TranslationIssue(
                    code="translation_provider_attempt_failed",
                    severity="warning",
                    message=str(exc),
                    segment_id=segment_id,
                    attempt=attempt,
                )
            )
            if attempt <= retry_count:
                continue
            state.consecutive_failures += 1
            if state.consecutive_failures >= circuit_failures:
                state.open_until_monotonic = time.monotonic() + circuit_reset_seconds
            fallback = _fallback_translate(text=text, source_language=source_language)
            issues.append(
                TranslationIssue(
                    code="translation_provider_fallback_used",
                    severity="error",
                    message=(
                        f"Provider '{provider.name}' failed after {retry_count + 1} attempts; "
                        "fallback translation applied."
                    ),
                    segment_id=segment_id,
                )
            )
            return fallback, "fallback.lexicon.v1", _fallback_quality(fallback, text), issues, True
    fallback = _fallback_translate(text=text, source_language=source_language)
    return fallback, "fallback.lexicon.v1", _fallback_quality(fallback, text), issues, True


def _resolve_language_id_provider() -> _HeuristicLanguageIdProvider:
    provider = os.environ.get("STORY_GEN_LANG_ID_PROVIDER", "heuristic.v2").strip().lower()
    if provider in {"", "heuristic.v2", "heuristic"}:
        return _HeuristicLanguageIdProvider()
    return _HeuristicLanguageIdProvider()


def _resolve_translation_provider() -> (
    _IdentityTranslationProvider | _LexiconTranslationProvider | _FailingTranslationProvider
):
    provider = os.environ.get("STORY_GEN_TRANSLATION_PROVIDER", "lexicon.v2").strip().lower()
    if provider in {"", "lexicon.v2", "lexicon"}:
        return _LexiconTranslationProvider()
    if provider in {"identity.v1", "identity"}:
        return _IdentityTranslationProvider()
    if provider in {"failing.v1", "failing"}:
        return _FailingTranslationProvider()
    return _LexiconTranslationProvider()


def _fallback_translate(*, text: str, source_language: str) -> str:
    replacements = _LANGUAGE_TO_MAP.get(source_language)
    if replacements is None:
        return text
    return _replace_tokens(text, replacements)


def _provider_quality(*, source_text: str, translated_text: str, source_language: str) -> float:
    if source_language in {"en", "und"}:
        return 1.0 if translated_text == source_text else 0.92
    if translated_text == source_text:
        return 0.35
    replacements = _LANGUAGE_TO_MAP.get(source_language)
    if replacements is None:
        return 0.76
    coverage = _replacement_coverage(source_text, replacements)
    if coverage <= 0.0:
        return 0.42
    edit_ratio = _token_edit_ratio(source_text, translated_text)
    quality = 0.7 + (coverage * 0.2) + min(0.08, edit_ratio * 0.1)
    return round(min(0.98, max(0.78, quality)), 3)


def _fallback_quality(translated_text: str, source_text: str) -> float:
    if translated_text == source_text:
        return 0.32
    return 0.52


def _replace_tokens(text: str, replacements: dict[str, str]) -> str:
    words = text.split()
    translated: list[str] = []
    for word in words:
        cleaned = word.strip(".,!?;:()[]{}\"'").lower()
        translated_word = replacements.get(cleaned)
        translated.append(translated_word if translated_word is not None else word)
    return " ".join(translated)


def _replacement_coverage(text: str, replacements: dict[str, str]) -> float:
    tokens = _tokens(text)
    if not tokens:
        return 0.0
    replaced = sum(1 for token in tokens if token in replacements)
    return replaced / len(tokens)


def _token_edit_ratio(source_text: str, translated_text: str) -> float:
    source_tokens = _tokens(source_text)
    translated_tokens = _tokens(translated_text)
    if not source_tokens:
        return 0.0
    changes = 0
    total = max(len(source_tokens), len(translated_tokens))
    for index in range(total):
        source = source_tokens[index] if index < len(source_tokens) else ""
        translated = translated_tokens[index] if index < len(translated_tokens) else ""
        if source != translated:
            changes += 1
    return changes / total


def _tokens(text: str) -> list[str]:
    return [token for token in _TOKEN_RE.findall(text.lower()) if token]


def _marker_score(tokens: list[str], markers: set[str]) -> float:
    if not tokens:
        return 0.0
    hits = sum(1 for token in tokens if token in markers)
    return hits / len(tokens)


def _majority_language(values: list[str]) -> str:
    if not values:
        return "und"
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    ordered = sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))
    return ordered[0][0]


def _int_env(name: str, *, default: int, minimum: int, maximum: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(minimum, min(maximum, value))
