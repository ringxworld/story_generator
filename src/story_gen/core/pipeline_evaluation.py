"""Fixture-driven QA evaluation harness for story pipeline regressions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any, Literal, cast

from story_gen.core.insight_engine import generate_insights
from story_gen.core.language_translation import translate_segments
from story_gen.core.narrative_analysis import detect_story_beats
from story_gen.core.quality_evaluation import evaluate_quality_gate
from story_gen.core.story_extraction import extract_events_and_entities
from story_gen.core.story_ingestion import IngestionRequest, ingest_story_text
from story_gen.core.story_schema import RawSegment, stable_id
from story_gen.core.theme_arc_tracking import track_theme_arc_signals
from story_gen.core.timeline_composer import compose_timeline


@dataclass(frozen=True)
class EvaluationFixtureCase:
    """One fixture case used by regression harness."""

    case_id: str
    description: str
    source_type: str
    source_text: str
    segments: tuple[str, ...]
    target_language: str
    tags: tuple[str, ...]
    expectations: dict[str, Any]


@dataclass(frozen=True)
class CalibrationConfig:
    """Calibration split and threshold configuration."""

    positive_tags: tuple[str, ...]
    negative_tags: tuple[str, ...]
    theme_confidence_floor: float
    arc_confidence_floor: float
    non_story_strength_ceiling: float


@dataclass(frozen=True)
class EvaluationFixtureSuite:
    """Complete fixture suite payload."""

    fixture_version: str
    cases: tuple[EvaluationFixtureCase, ...]
    calibration: CalibrationConfig


def load_fixture_suite(path: Path) -> EvaluationFixtureSuite:
    """Load and validate fixture suite JSON."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Fixture suite must be a JSON object.")
    fixture_version = _required_str(raw, "fixture_version")
    raw_cases = raw.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise ValueError("Fixture suite must contain non-empty 'cases'.")
    cases = tuple(_parse_case(item) for item in raw_cases)
    raw_calibration = raw.get("calibration")
    if not isinstance(raw_calibration, dict):
        raise ValueError("Fixture suite must contain 'calibration' object.")
    thresholds = raw_calibration.get("thresholds")
    if not isinstance(thresholds, dict):
        raise ValueError("Fixture suite calibration must contain 'thresholds'.")
    calibration = CalibrationConfig(
        positive_tags=tuple(_required_str_list(raw_calibration, "positive_tags")),
        negative_tags=tuple(_required_str_list(raw_calibration, "negative_tags")),
        theme_confidence_floor=_required_float(thresholds, "theme_confidence_floor"),
        arc_confidence_floor=_required_float(thresholds, "arc_confidence_floor"),
        non_story_strength_ceiling=_required_float(thresholds, "non_story_strength_ceiling"),
    )
    return EvaluationFixtureSuite(
        fixture_version=fixture_version,
        cases=cases,
        calibration=calibration,
    )


def evaluate_fixture_suite(*, suite: EvaluationFixtureSuite) -> dict[str, Any]:
    """Run evaluation suite and return deterministic JSON-serializable summary."""
    case_results: list[dict[str, Any]] = []
    for case in suite.cases:
        case_results.append(_evaluate_case(case))

    calibration_summary = _evaluate_calibration(
        case_results=case_results,
        config=suite.calibration,
    )
    failed_cases = [result for result in case_results if result["status"] == "failed"]
    status = (
        "passed" if not failed_cases and calibration_summary["status"] == "passed" else "failed"
    )
    all_alignment_scores = [
        float(item["quality_score"])
        for result in case_results
        for item in result["alignment_scores"]
        if isinstance(item, dict) and "quality_score" in item
    ]
    all_theme_confidences = [
        float(result["metrics"]["non_story_theme_confidence_min"])
        for result in case_results
        if float(result["metrics"]["non_story_theme_confidence_min"]) > 0.0
    ]
    all_arc_confidences = [
        float(result["metrics"]["arc_confidence_min"])
        for result in case_results
        if float(result["metrics"]["arc_confidence_min"]) > 0.0
    ]
    return {
        "status": status,
        "fixture_version": suite.fixture_version,
        "evaluated_at_utc": datetime.now(UTC).isoformat(),
        "totals": {
            "cases": len(case_results),
            "passed": len(case_results) - len(failed_cases),
            "failed": len(failed_cases),
        },
        "confidence_distributions": {
            "alignment_quality": _distribution(all_alignment_scores),
            "non_story_theme_confidence": _distribution(all_theme_confidences),
            "arc_confidence": _distribution(all_arc_confidences),
        },
        "calibration": calibration_summary,
        "cases": case_results,
    }


def _evaluate_case(case: EvaluationFixtureCase) -> dict[str, Any]:
    translated_source_segments: list[RawSegment]
    if case.segments:
        translated_source_segments = _segments_from_fixture(
            case_id=case.case_id,
            source_type=case.source_type,
            texts=list(case.segments),
        )
    else:
        artifact = ingest_story_text(
            IngestionRequest(
                source_type=case.source_type,
                source_text=case.source_text,
                idempotency_key=f"qa:{case.case_id}",
            )
        )
        translated_source_segments = artifact.segments
    translated_segments, alignments, source_language = translate_segments(
        segments=translated_source_segments,
        target_language=case.target_language,
    )
    language_distribution = _language_distribution(
        segments=translated_segments,
        target_language=case.target_language,
    )
    events, entities = extract_events_and_entities(segments=translated_segments)
    beats = detect_story_beats(events=events)
    themes, arcs, conflicts, emotions = track_theme_arc_signals(beats=beats, entities=entities)
    timeline = compose_timeline(events=events, beats=beats)
    insights = generate_insights(beats=beats, themes=themes)
    quality_gate, evaluation_metrics = evaluate_quality_gate(
        segments=translated_segments,
        insights=insights,
        timeline_consistency=timeline.consistency_score,
    )

    alignment_values = [alignment.quality_score for alignment in alignments]
    alignment_mean = _round(mean(alignment_values)) if alignment_values else 0.0
    alignment_min = _round(min(alignment_values)) if alignment_values else 0.0
    beat_stage_sequence = [beat.stage for beat in beats]
    theme_labels = sorted({theme.label for theme in themes})
    non_story_signals = [signal for signal in themes if signal.label != "story"]
    non_story_strength_max = _round(
        max((signal.strength for signal in non_story_signals), default=0.0)
    )
    non_story_confidence_min = _round(
        min((signal.confidence.score for signal in non_story_signals), default=0.0)
    )
    arc_confidence_min = _round(min((arc.confidence for arc in arcs), default=0.0))
    timeline_conflict_codes = sorted({conflict.code for conflict in timeline.conflicts})
    metrics: dict[str, Any] = {
        "source_language": source_language,
        "source_language_distribution": language_distribution["counts"],
        "detected_languages": language_distribution["languages"],
        "non_target_language_segment_count": language_distribution["non_target_count"],
        "non_target_language_segment_share": language_distribution["non_target_share"],
        "segment_count": len(translated_segments),
        "event_count": len(events),
        "beat_count": len(beats),
        "beat_stage_sequence": beat_stage_sequence,
        "theme_labels": theme_labels,
        "non_story_theme_strength_max": non_story_strength_max,
        "non_story_theme_confidence_min": non_story_confidence_min,
        "arc_confidence_min": arc_confidence_min,
        "timeline_conflict_count": len(timeline.conflicts),
        "timeline_conflict_codes": timeline_conflict_codes,
        "timeline_consistency": _round(timeline.consistency_score),
        "insight_count": len(insights),
        "insight_granularities": sorted({insight.granularity for insight in insights}),
        "quality_gate_passed": quality_gate.passed,
        "hallucination_risk": _round(evaluation_metrics.hallucination_risk),
        "translation_quality": _round(evaluation_metrics.translation_quality),
        "alignment_mean": alignment_mean,
        "alignment_min": alignment_min,
    }
    failures = _evaluate_expectations(case.expectations, metrics)
    return {
        "case_id": case.case_id,
        "description": case.description,
        "tags": list(case.tags),
        "status": "failed" if failures else "passed",
        "failures": failures,
        "alignment_scores": [
            {
                "segment_id": alignment.source_segment_id,
                "quality_score": _round(alignment.quality_score),
                "method": alignment.method,
            }
            for alignment in alignments
        ],
        "metrics": metrics,
    }


def _evaluate_expectations(expectations: dict[str, Any], metrics: dict[str, Any]) -> list[str]:
    failures: list[str] = []

    _min_check(expectations, metrics, "min_alignment_mean", "alignment_mean", failures)
    _min_check(expectations, metrics, "min_alignment_min", "alignment_min", failures)
    _min_check(expectations, metrics, "min_event_count", "event_count", failures)
    _min_check(expectations, metrics, "min_beat_count", "beat_count", failures)
    _min_check(expectations, metrics, "min_insight_count", "insight_count", failures)
    _min_check(expectations, metrics, "min_translation_quality", "translation_quality", failures)
    _min_check(expectations, metrics, "min_timeline_consistency", "timeline_consistency", failures)
    _min_check(
        expectations,
        metrics,
        "min_non_target_language_segments",
        "non_target_language_segment_count",
        failures,
    )
    _min_check(
        expectations,
        metrics,
        "min_non_target_language_share",
        "non_target_language_segment_share",
        failures,
    )
    _min_check(
        expectations,
        metrics,
        "min_non_story_theme_confidence",
        "non_story_theme_confidence_min",
        failures,
    )
    _min_check(expectations, metrics, "min_arc_confidence", "arc_confidence_min", failures)

    _max_check(expectations, metrics, "max_hallucination_risk", "hallucination_risk", failures)
    _max_check(
        expectations,
        metrics,
        "max_timeline_conflicts",
        "timeline_conflict_count",
        failures,
    )
    _max_check(
        expectations,
        metrics,
        "max_timeline_consistency",
        "timeline_consistency",
        failures,
    )
    _max_check(
        expectations,
        metrics,
        "max_non_story_theme_strength",
        "non_story_theme_strength_max",
        failures,
    )

    expected_sequence = expectations.get("expected_beat_stage_sequence")
    if expected_sequence is not None:
        expected = _expect_str_list(expected_sequence, "expected_beat_stage_sequence")
        actual = metrics["beat_stage_sequence"]
        if actual != expected:
            failures.append(
                f"expected_beat_stage_sequence mismatch: expected={expected}, actual={actual}"
            )

    _subset_check(
        expectations,
        metrics,
        "required_beat_stages",
        "beat_stage_sequence",
        failures,
    )
    _subset_check(
        expectations,
        metrics,
        "required_detected_languages",
        "detected_languages",
        failures,
    )
    _subset_check(
        expectations,
        metrics,
        "required_theme_labels",
        "theme_labels",
        failures,
    )
    _subset_check(
        expectations,
        metrics,
        "required_timeline_conflict_codes",
        "timeline_conflict_codes",
        failures,
    )
    _subset_check(
        expectations,
        metrics,
        "required_insight_granularities",
        "insight_granularities",
        failures,
    )

    forbidden_labels = expectations.get("forbidden_theme_labels")
    if forbidden_labels is not None:
        forbidden = set(_expect_str_list(forbidden_labels, "forbidden_theme_labels"))
        labels = set(_expect_str_list(metrics["theme_labels"], "theme_labels"))
        overlap = sorted(forbidden.intersection(labels))
        if overlap:
            failures.append(f"forbidden_theme_labels present: {overlap}")
    return failures


def _evaluate_calibration(
    *,
    case_results: list[dict[str, Any]],
    config: CalibrationConfig,
) -> dict[str, Any]:
    positive_rows = [
        row for row in case_results if any(tag in set(row["tags"]) for tag in config.positive_tags)
    ]
    negative_rows = [
        row for row in case_results if any(tag in set(row["tags"]) for tag in config.negative_tags)
    ]
    failures: list[str] = []
    if not positive_rows:
        failures.append("no calibration-positive fixtures evaluated")
    if not negative_rows:
        failures.append("no calibration-negative fixtures evaluated")

    positive_theme_floor = _round(
        min(
            (
                float(row["metrics"]["non_story_theme_confidence_min"])
                for row in positive_rows
                if float(row["metrics"]["non_story_theme_confidence_min"]) > 0.0
            ),
            default=0.0,
        )
    )
    positive_arc_floor = _round(
        min(
            (
                float(row["metrics"]["arc_confidence_min"])
                for row in positive_rows
                if float(row["metrics"]["arc_confidence_min"]) > 0.0
            ),
            default=0.0,
        )
    )
    negative_non_story_ceiling = _round(
        max(
            (float(row["metrics"]["non_story_theme_strength_max"]) for row in negative_rows),
            default=0.0,
        )
    )

    if positive_theme_floor < config.theme_confidence_floor:
        failures.append(
            "theme confidence calibration failed: "
            f"observed={positive_theme_floor}, required>={config.theme_confidence_floor}"
        )
    if positive_arc_floor < config.arc_confidence_floor:
        failures.append(
            "arc confidence calibration failed: "
            f"observed={positive_arc_floor}, required>={config.arc_confidence_floor}"
        )
    if negative_non_story_ceiling > config.non_story_strength_ceiling:
        failures.append(
            "hard-negative non-story strength calibration failed: "
            f"observed={negative_non_story_ceiling}, "
            f"required<={config.non_story_strength_ceiling}"
        )

    return {
        "status": "failed" if failures else "passed",
        "positive_case_count": len(positive_rows),
        "negative_case_count": len(negative_rows),
        "observed": {
            "theme_confidence_floor": positive_theme_floor,
            "arc_confidence_floor": positive_arc_floor,
            "non_story_strength_ceiling": negative_non_story_ceiling,
        },
        "configured": {
            "theme_confidence_floor": _round(config.theme_confidence_floor),
            "arc_confidence_floor": _round(config.arc_confidence_floor),
            "non_story_strength_ceiling": _round(config.non_story_strength_ceiling),
        },
        "failures": failures,
    }


def _distribution(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0, "min": None, "mean": None, "max": None}
    return {
        "count": len(values),
        "min": _round(min(values)),
        "mean": _round(mean(values)),
        "max": _round(max(values)),
    }


def _parse_case(raw: object) -> EvaluationFixtureCase:
    if not isinstance(raw, dict):
        raise ValueError("Fixture case must be an object.")
    expectations = raw.get("expectations")
    if not isinstance(expectations, dict):
        raise ValueError("Fixture case must contain object 'expectations'.")
    return EvaluationFixtureCase(
        case_id=_required_str(raw, "case_id"),
        description=_required_str(raw, "description"),
        source_type=_required_str(raw, "source_type"),
        source_text=_required_str(raw, "source_text"),
        segments=tuple(_optional_str_list(raw, "segments")),
        target_language=str(raw.get("target_language", "en")),
        tags=tuple(_required_str_list(raw, "tags")),
        expectations=dict(expectations),
    )


def _segments_from_fixture(*, case_id: str, source_type: str, texts: list[str]) -> list[RawSegment]:
    segments: list[RawSegment] = []
    source_kind: Literal["text", "document", "transcript"] = "text"
    if source_type in {"text", "document", "transcript"}:
        source_kind = cast(Literal["text", "document", "transcript"], source_type)
    char_cursor = 0
    for index, text in enumerate(texts, start=1):
        cleaned = text.strip()
        if not cleaned:
            continue
        segment_id = stable_id(prefix="seg", text=f"qa:{case_id}:{index}:{cleaned}")
        segment = RawSegment(
            segment_id=segment_id,
            source_type=source_kind,
            original_text=cleaned,
            normalized_text=cleaned,
            translated_text=None,
            segment_index=index,
            char_start=char_cursor,
            char_end=char_cursor + len(cleaned),
        )
        char_cursor = segment.char_end + 1
        segments.append(segment)
    if not segments:
        raise ValueError(f"Fixture case {case_id} produced no usable segments.")
    return segments


def _language_distribution(
    *,
    segments: list[RawSegment],
    target_language: str,
) -> dict[str, Any]:
    counts: dict[str, int] = {}
    normalized_target = target_language.strip().lower()
    non_target_count = 0
    for segment in segments:
        language = segment.language_code.strip().lower() or "und"
        counts[language] = counts.get(language, 0) + 1
        if language not in {normalized_target, "und"}:
            non_target_count += 1
    languages = sorted(counts)
    total_segments = len(segments)
    non_target_share = _round(non_target_count / total_segments) if total_segments else 0.0
    return {
        "counts": counts,
        "languages": languages,
        "non_target_count": non_target_count,
        "non_target_share": non_target_share,
    }


def _subset_check(
    expectations: dict[str, Any],
    metrics: dict[str, Any],
    expectation_key: str,
    metric_key: str,
    failures: list[str],
) -> None:
    if expectation_key not in expectations:
        return
    required = set(_expect_str_list(expectations[expectation_key], expectation_key))
    observed = set(_expect_str_list(metrics[metric_key], metric_key))
    missing = sorted(required.difference(observed))
    if missing:
        failures.append(f"{expectation_key} missing values: {missing}")


def _min_check(
    expectations: dict[str, Any],
    metrics: dict[str, Any],
    expectation_key: str,
    metric_key: str,
    failures: list[str],
) -> None:
    if expectation_key not in expectations:
        return
    required = float(expectations[expectation_key])
    actual = float(metrics[metric_key])
    if actual < required:
        failures.append(
            f"{metric_key} too low: actual={_round(actual)}, required>={_round(required)}"
        )


def _max_check(
    expectations: dict[str, Any],
    metrics: dict[str, Any],
    expectation_key: str,
    metric_key: str,
    failures: list[str],
) -> None:
    if expectation_key not in expectations:
        return
    allowed = float(expectations[expectation_key])
    actual = float(metrics[metric_key])
    if actual > allowed:
        failures.append(
            f"{metric_key} too high: actual={_round(actual)}, required<={_round(allowed)}"
        )


def _expect_str_list(raw: object, field: str) -> list[str]:
    if not isinstance(raw, list):
        raise ValueError(f"Expected list[str] for {field}.")
    values: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            raise ValueError(f"Expected string list item in {field}.")
        normalized = item.strip()
        if normalized:
            values.append(normalized)
    return values


def _required_str(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if isinstance(value, str) and value.strip():
        return value
    raise ValueError(f"Missing or invalid string field '{key}'.")


def _required_str_list(data: dict[str, Any], key: str) -> list[str]:
    value = data.get(key)
    return _expect_str_list(value, key)


def _optional_str_list(data: dict[str, Any], key: str) -> list[str]:
    value = data.get(key)
    if value is None:
        return []
    return _expect_str_list(value, key)


def _required_float(data: dict[str, Any], key: str) -> float:
    value = data.get(key)
    if isinstance(value, bool):
        raise ValueError(f"Invalid float field '{key}' (bool).")
    if isinstance(value, (int, float)):
        return float(value)
    raise ValueError(f"Missing or invalid float field '{key}'.")


def _round(value: float) -> float:
    return round(float(value), 3)
