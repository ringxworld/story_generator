"""Deterministic quality checks for structured essay workflows."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

WORD_PATTERN = re.compile(r"[A-Za-z0-9']+")
CITATION_PATTERN = re.compile(
    r"\[[0-9]+\]|\([A-Za-z][^)]*,\s*[0-9]{4}\)|according to",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class EssaySectionSpec:
    """Required section contract for one essay."""

    key: str
    purpose: str
    min_paragraphs: int = 1
    required_terms: tuple[str, ...] = ()


@dataclass(frozen=True)
class EssayPolicySpec:
    """Validation policy used to evaluate one essay draft."""

    thesis_statement: str
    audience: str
    tone: str
    min_words: int
    max_words: int
    required_sections: tuple[EssaySectionSpec, ...]
    banned_phrases: tuple[str, ...] = ()
    required_citations: int = 0


@dataclass(frozen=True)
class EssayDraftInput:
    """Draft payload passed into the deterministic evaluator."""

    title: str
    prompt: str
    draft_text: str
    policy: EssayPolicySpec


@dataclass(frozen=True)
class EssayQualityCheck:
    """One quality check finding."""

    code: str
    severity: Literal["error", "warning"]
    message: str


@dataclass(frozen=True)
class EssayQualityResult:
    """Aggregated evaluation output."""

    word_count: int
    citation_count: int
    score: float
    passed: bool
    checks: tuple[EssayQualityCheck, ...] = field(default_factory=tuple)


def _paragraphs(text: str) -> list[str]:
    return [chunk.strip() for chunk in re.split(r"\n\s*\n", text) if chunk.strip()]


def _word_count(text: str) -> int:
    return len(WORD_PATTERN.findall(text))


def _citation_count(text: str) -> int:
    return len(CITATION_PATTERN.findall(text))


def _normalized_tokens(text: str) -> set[str]:
    return {token.lower() for token in WORD_PATTERN.findall(text) if len(token) >= 4}


def evaluate_essay_quality(draft: EssayDraftInput) -> EssayQualityResult:
    """Evaluate one draft against policy checks and return pass/fail details."""
    checks: list[EssayQualityCheck] = []
    word_count = _word_count(draft.draft_text)
    citation_count = _citation_count(draft.draft_text)
    text_lower = draft.draft_text.lower()

    if word_count < draft.policy.min_words or word_count > draft.policy.max_words:
        checks.append(
            EssayQualityCheck(
                code="word_count_out_of_range",
                severity="error",
                message=(
                    f"Word count {word_count} is outside "
                    f"[{draft.policy.min_words}, {draft.policy.max_words}]."
                ),
            )
        )

    if citation_count < draft.policy.required_citations:
        checks.append(
            EssayQualityCheck(
                code="insufficient_citations",
                severity="error",
                message=(
                    f"Citation count {citation_count} is below required "
                    f"{draft.policy.required_citations}."
                ),
            )
        )

    for phrase in draft.policy.banned_phrases:
        if phrase and phrase.lower() in text_lower:
            checks.append(
                EssayQualityCheck(
                    code="banned_phrase_present",
                    severity="error",
                    message=f"Draft contains banned phrase: '{phrase}'.",
                )
            )

    paragraphs = _paragraphs(draft.draft_text)
    first_paragraph = paragraphs[0] if paragraphs else ""
    thesis_tokens = _normalized_tokens(draft.policy.thesis_statement)
    first_paragraph_tokens = _normalized_tokens(first_paragraph)
    if thesis_tokens and thesis_tokens.isdisjoint(first_paragraph_tokens):
        checks.append(
            EssayQualityCheck(
                code="thesis_not_introduced_early",
                severity="warning",
                message="The opening paragraph does not appear to reflect thesis language.",
            )
        )

    for section in draft.policy.required_sections:
        marker = section.key.lower()
        if marker not in text_lower:
            checks.append(
                EssayQualityCheck(
                    code="missing_required_section",
                    severity="error",
                    message=f"Draft is missing required section marker: '{section.key}'.",
                )
            )
            continue

        section_paragraphs = [paragraph for paragraph in paragraphs if marker in paragraph.lower()]
        if len(section_paragraphs) < section.min_paragraphs:
            checks.append(
                EssayQualityCheck(
                    code="section_too_short",
                    severity="warning",
                    message=(
                        f"Section '{section.key}' has {len(section_paragraphs)} paragraph(s), "
                        f"expected at least {section.min_paragraphs}."
                    ),
                )
            )
        for term in section.required_terms:
            if term and term.lower() not in text_lower:
                checks.append(
                    EssayQualityCheck(
                        code="required_term_missing",
                        severity="warning",
                        message=f"Required term '{term}' is missing.",
                    )
                )

    score = 100.0
    for check in checks:
        if check.severity == "error":
            score -= 20.0
        else:
            score -= 8.0
    score = max(0.0, score)
    passed = all(check.severity != "error" for check in checks)

    return EssayQualityResult(
        word_count=word_count,
        citation_count=citation_count,
        score=score,
        passed=passed,
        checks=tuple(checks),
    )
