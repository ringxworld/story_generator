"""Evaluation and confidence gate for story intelligence outputs."""

from __future__ import annotations

import re
from dataclasses import dataclass

from story_gen.core.story_schema import Insight, QualityGate, RawSegment

_WORD_TOKEN = re.compile(r"[A-Za-z']+")


@dataclass(frozen=True)
class EvaluationMetrics:
    """Evaluation metrics reported by quality stage."""

    confidence_floor: float
    hallucination_risk: float
    translation_quality: float
    timeline_consistency: float
    insight_evidence_consistency: float
    inconsistent_insight_ids: tuple[str, ...]


def evaluate_quality_gate(
    *,
    segments: list[RawSegment],
    insights: list[Insight],
    timeline_consistency: float = 1.0,
    confidence_threshold: float = 0.55,
    evidence_consistency_threshold: float = 0.58,
) -> tuple[QualityGate, EvaluationMetrics]:
    """Evaluate analysis quality before dashboard exposure."""
    if not segments:
        raise ValueError("segments are required for quality evaluation.")
    if not insights:
        raise ValueError("insights are required for quality evaluation.")

    confidence_floor = min(insight.confidence.score for insight in insights)
    hallucination_risk = _hallucination_risk(segments=segments, insights=insights)
    translation_quality = _translation_quality(segments)
    evidence_consistency, inconsistent_ids = _insight_evidence_consistency(
        segments=segments,
        insights=insights,
    )
    timeline_consistency = max(0.0, min(1.0, timeline_consistency))
    passed = (
        confidence_floor >= confidence_threshold
        and hallucination_risk <= 0.45
        and translation_quality >= 0.5
        and timeline_consistency >= 0.55
        and evidence_consistency >= evidence_consistency_threshold
    )
    reasons: list[str] = []
    if confidence_floor < confidence_threshold:
        reasons.append("confidence_below_threshold")
    if hallucination_risk > 0.45:
        reasons.append("hallucination_risk_high")
    if translation_quality < 0.5:
        reasons.append("translation_quality_low")
    if timeline_consistency < 0.55:
        reasons.append("timeline_consistency_low")
    if evidence_consistency < evidence_consistency_threshold:
        reasons.append("insight_evidence_inconsistent")

    metrics = EvaluationMetrics(
        confidence_floor=round(confidence_floor, 3),
        hallucination_risk=round(hallucination_risk, 3),
        translation_quality=round(translation_quality, 3),
        timeline_consistency=round(timeline_consistency, 3),
        insight_evidence_consistency=round(evidence_consistency, 3),
        inconsistent_insight_ids=tuple(sorted(inconsistent_ids)),
    )
    gate = QualityGate(
        passed=passed,
        confidence_floor=metrics.confidence_floor,
        hallucination_risk=metrics.hallucination_risk,
        translation_quality=metrics.translation_quality,
        reasons=reasons,
    )
    return gate, metrics


def _hallucination_risk(*, segments: list[RawSegment], insights: list[Insight]) -> float:
    segment_ids = {segment.segment_id for segment in segments}
    invalid_links = 0
    total_links = 0
    for insight in insights:
        for segment_id in insight.evidence_segment_ids:
            total_links += 1
            if segment_id not in segment_ids:
                invalid_links += 1
    if total_links == 0:
        return 1.0
    return invalid_links / total_links


def _translation_quality(segments: list[RawSegment]) -> float:
    translated = [segment for segment in segments if segment.translated_text is not None]
    if not translated:
        return 1.0
    unchanged = 0
    for segment in translated:
        if segment.translated_text == segment.normalized_text and segment.language_code not in {
            "en",
            "und",
        }:
            unchanged += 1
    return 1.0 - (unchanged / len(translated))


def _insight_evidence_consistency(
    *,
    segments: list[RawSegment],
    insights: list[Insight],
) -> tuple[float, set[str]]:
    segment_tokens = {
        segment.segment_id: _tokenize(segment.translated_text or segment.normalized_text)
        for segment in segments
    }
    consistent = 0
    inconsistent_ids: set[str] = set()
    for insight in insights:
        evidence_tokens: set[str] = set()
        for segment_id in insight.evidence_segment_ids:
            evidence_tokens.update(segment_tokens.get(segment_id, set()))
        insight_tokens = _tokenize(insight.content)
        if not insight_tokens:
            inconsistent_ids.add(insight.insight_id)
            continue
        overlap = len(evidence_tokens.intersection(insight_tokens)) / len(insight_tokens)
        if overlap < 0.08:
            inconsistent_ids.add(insight.insight_id)
            continue
        consistent += 1
    total = len(insights)
    if total <= 0:
        return 0.0, inconsistent_ids
    return consistent / total, inconsistent_ids


def _tokenize(text: str) -> set[str]:
    return {token.lower() for token in _WORD_TOKEN.findall(text) if len(token) >= 3}
