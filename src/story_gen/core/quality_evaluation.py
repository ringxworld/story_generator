"""Evaluation and confidence gate for story intelligence outputs."""

from __future__ import annotations

from dataclasses import dataclass

from story_gen.core.story_schema import Insight, QualityGate, RawSegment


@dataclass(frozen=True)
class EvaluationMetrics:
    """Evaluation metrics reported by quality stage."""

    confidence_floor: float
    hallucination_risk: float
    translation_quality: float


def evaluate_quality_gate(
    *,
    segments: list[RawSegment],
    insights: list[Insight],
    confidence_threshold: float = 0.55,
) -> tuple[QualityGate, EvaluationMetrics]:
    """Evaluate analysis quality before dashboard exposure."""
    if not segments:
        raise ValueError("segments are required for quality evaluation.")
    if not insights:
        raise ValueError("insights are required for quality evaluation.")

    confidence_floor = min(insight.confidence.score for insight in insights)
    hallucination_risk = _hallucination_risk(segments=segments, insights=insights)
    translation_quality = _translation_quality(segments)
    passed = (
        confidence_floor >= confidence_threshold
        and hallucination_risk <= 0.45
        and translation_quality >= 0.5
    )
    reasons: list[str] = []
    if confidence_floor < confidence_threshold:
        reasons.append("confidence_below_threshold")
    if hallucination_risk > 0.45:
        reasons.append("hallucination_risk_high")
    if translation_quality < 0.5:
        reasons.append("translation_quality_low")

    metrics = EvaluationMetrics(
        confidence_floor=round(confidence_floor, 3),
        hallucination_risk=round(hallucination_risk, 3),
        translation_quality=round(translation_quality, 3),
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
        if segment.translated_text == segment.normalized_text and segment.language_code not in {"en", "und"}:
            unchanged += 1
    return 1.0 - (unchanged / len(translated))

