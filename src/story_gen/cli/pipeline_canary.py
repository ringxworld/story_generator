"""Pipeline canary command for end-to-end stage validation."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from story_gen.core.dashboard_views import build_dashboard_read_model, export_graph_svg
from story_gen.core.insight_engine import generate_insights
from story_gen.core.language_translation import translate_segments
from story_gen.core.narrative_analysis import detect_story_beats
from story_gen.core.pipeline_contracts import (
    validate_beat_input,
    validate_beat_output,
    validate_extraction_input,
    validate_extraction_output,
    validate_insight_input,
    validate_insight_output,
    validate_theme_input,
    validate_theme_output,
    validate_timeline_input,
    validate_timeline_output,
)
from story_gen.core.quality_evaluation import evaluate_quality_gate
from story_gen.core.story_extraction import extract_events_and_entities
from story_gen.core.story_ingestion import IngestionRequest, ingest_story_text
from story_gen.core.story_schema import StoryDocument
from story_gen.core.theme_arc_tracking import track_theme_arc_signals
from story_gen.core.timeline_composer import compose_timeline


@dataclass(frozen=True)
class StageCheck:
    stage: str
    status: str
    details: dict[str, object]


@dataclass(frozen=True)
class CanaryVariant:
    variant_id: str
    description: str
    source_type: str
    target_language: str
    source_text: str


class CanaryStageError(RuntimeError):
    """Raised when one canary stage fails."""

    def __init__(self, *, stage: str, error: Exception, checks: list[StageCheck]) -> None:
        super().__init__(str(error))
        self.stage = stage
        self.error = error
        self.checks = checks


DEFAULT_SOURCE_TEXT = (
    "[00:01] Narrator: Rhea enters the archive and finds her family's ledger.\n"
    "[00:40] Council: The council denies the records and tension rises.\n"
    "[01:10] Rhea: She confronts the council in the central hall.\n"
    "[01:42] Narrator: The city accepts the truth and begins to heal.\n"
)
SPANISH_SOURCE_TEXT = (
    "[00:01] Narrador: La historia de la familia protege la memoria.\n"
    "[00:45] Consejo: El consejo niega el archivo y el conflicto crece.\n"
    "[01:20] Rhea: Ella confronta al consejo y busca la verdad.\n"
    "[01:50] Narrador: La ciudad acepta la verdad y sana.\n"
)
CODE_SWITCH_SOURCE_TEXT = (
    "[00:02] Narrator: La historia starts in the archive with missing records.\n"
    "[00:36] Council: El consejo denies the ledger and tension rises.\n"
    "[01:05] Rhea: Ella confronts the council in public.\n"
    "[01:42] Narrator: The city accepts la verdad and starts to heal.\n"
)
DOCUMENT_SOURCE_TEXT = (
    "# Incident Report\n"
    "1. 2024-01-03 Rhea enters the archive and finds conflicting records.\n"
    "2. 2024-01-04 The council denies the evidence.\n"
    "3. 2024-01-05 Rhea presents the ledger in the central hall.\n"
    "4. 2024-01-06 The city accepts the truth.\n"
)
DEFAULT_VARIANTS: Final[dict[str, CanaryVariant]] = {
    "default_transcript_en": CanaryVariant(
        variant_id="default_transcript_en",
        description="Baseline transcript path in English.",
        source_type="transcript",
        target_language="en",
        source_text=DEFAULT_SOURCE_TEXT,
    ),
    "multilingual_transcript_es": CanaryVariant(
        variant_id="multilingual_transcript_es",
        description="Non-English transcript path with Spanish markers and translation alignment.",
        source_type="transcript",
        target_language="en",
        source_text=SPANISH_SOURCE_TEXT,
    ),
    "code_switch_transcript_es_en": CanaryVariant(
        variant_id="code_switch_transcript_es_en",
        description="Code-switch transcript with mixed Spanish and English cues.",
        source_type="transcript",
        target_language="en",
        source_text=CODE_SWITCH_SOURCE_TEXT,
    ),
    "document_timeline_en": CanaryVariant(
        variant_id="document_timeline_en",
        description="Document source adaptation path with deterministic chronology markers.",
        source_type="document",
        target_language="en",
        source_text=DOCUMENT_SOURCE_TEXT,
    ),
}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run deterministic end-to-end canary checks across all pipeline stages."
    )
    parser.add_argument("--story-id", default="story-canary")
    parser.add_argument(
        "--source-type", choices=["text", "document", "transcript"], default="transcript"
    )
    parser.add_argument("--target-language", default="en")
    parser.add_argument("--source-file", default=None)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument(
        "--variant",
        action="append",
        default=None,
        help=(
            "Run named built-in or fixture-defined variant(s). Repeat flag to run multiple variants."
        ),
    )
    parser.add_argument(
        "--run-all-variants",
        action="store_true",
        help="Run all variants from fixture file (or built-ins if no fixture file provided).",
    )
    parser.add_argument(
        "--variants-file",
        default=None,
        help=(
            "Optional JSON file with canary variants. Schema: "
            "{fixture_version, variants:[{variant_id,description,source_type,target_language,source_text}]}"
        ),
    )
    parser.add_argument(
        "--matrix-output",
        default=None,
        help="Optional path to persist matrix JSON summary for CI artifacts.",
    )
    return parser


def _load_source(source_file: str | None, *, source_type: str) -> str:
    if source_file is None:
        return (
            DEFAULT_SOURCE_TEXT
            if source_type == "transcript"
            else DEFAULT_SOURCE_TEXT.replace("[", "").replace("]", "")
        )
    path = Path(source_file)
    return path.read_text(encoding="utf-8")


def _load_variant_catalog(variants_file: str | None) -> tuple[dict[str, CanaryVariant], str]:
    if variants_file is None:
        return dict(DEFAULT_VARIANTS), "pipeline_canary_variants.v1.built_in"
    path = Path(variants_file)
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_variants = payload.get("variants")
    if not isinstance(raw_variants, list):
        raise ValueError("variants_file must include a list under 'variants'.")
    catalog: dict[str, CanaryVariant] = {}
    for raw in raw_variants:
        if not isinstance(raw, dict):
            raise ValueError("Each variant entry must be an object.")
        variant = CanaryVariant(
            variant_id=str(raw["variant_id"]),
            description=str(raw["description"]),
            source_type=str(raw["source_type"]),
            target_language=str(raw["target_language"]),
            source_text=str(raw["source_text"]),
        )
        if variant.source_type not in {"text", "document", "transcript"}:
            raise ValueError(
                f"Variant '{variant.variant_id}' has unsupported source_type '{variant.source_type}'."
            )
        if variant.variant_id in catalog:
            raise ValueError(f"Duplicate variant_id '{variant.variant_id}' in variants_file.")
        catalog[variant.variant_id] = variant
    fixture_version = str(payload.get("fixture_version", "pipeline_canary_variants.v1"))
    return catalog, fixture_version


def _select_variants(
    *,
    catalog: dict[str, CanaryVariant],
    requested_ids: list[str] | None,
    run_all_variants: bool,
) -> list[CanaryVariant]:
    if run_all_variants:
        return list(catalog.values())
    if not requested_ids:
        return []
    ordered_ids: list[str] = []
    for value in requested_ids:
        if value not in ordered_ids:
            ordered_ids.append(value)
    missing = [value for value in ordered_ids if value not in catalog]
    if missing:
        available = ", ".join(sorted(catalog))
        raise ValueError(
            f"Unknown canary variant(s): {', '.join(sorted(missing))}. Available: {available}"
        )
    return [catalog[variant_id] for variant_id in ordered_ids]


def _checks_to_stage_diagnostics(checks: list[StageCheck]) -> dict[str, dict[str, object]]:
    diagnostics: dict[str, dict[str, object]] = {}
    for check in checks:
        diagnostics[check.stage] = dict(check.details)
    return diagnostics


def _key_metrics(stage_diagnostics: dict[str, dict[str, object]]) -> dict[str, object]:
    return {
        "segments": stage_diagnostics.get("ingestion", {}).get("segments", 0),
        "alignments": stage_diagnostics.get("translation", {}).get("alignments", 0),
        "events": stage_diagnostics.get("extraction", {}).get("events", 0),
        "beats": stage_diagnostics.get("beat_detection", {}).get("beats", 0),
        "themes": stage_diagnostics.get("theme_tracking", {}).get("themes", 0),
        "arcs": stage_diagnostics.get("theme_tracking", {}).get("arcs", 0),
        "timeline_actual_points": stage_diagnostics.get("timeline", {}).get(
            "actual_time_points", 0
        ),
        "timeline_narrative_points": stage_diagnostics.get("timeline", {}).get(
            "narrative_points", 0
        ),
        "insights": stage_diagnostics.get("insights", {}).get("insights", 0),
        "graph_nodes": stage_diagnostics.get("dashboard_projection", {}).get("graph_nodes", 0),
        "graph_edges": stage_diagnostics.get("dashboard_projection", {}).get("graph_edges", 0),
    }


def _failure_payload(*, error: CanaryStageError) -> dict[str, object]:
    checks = [asdict(check) for check in error.checks]
    return {
        "status": "failed",
        "failed_stage": error.stage,
        "error": str(error.error),
        "checks": checks,
    }


def _run_variant(*, variant: CanaryVariant, strict: bool) -> dict[str, object]:
    story_id = f"story-canary-{variant.variant_id}"
    try:
        payload = run_canary(
            story_id=story_id,
            source_text=variant.source_text,
            source_type=variant.source_type,
            target_language=variant.target_language,
            strict=strict,
        )
        raw_checks = payload.get("checks")
        if not isinstance(raw_checks, list):
            raise ValueError("Canary payload must include a checks list.")
        checks = []
        for raw_check in raw_checks:
            if not isinstance(raw_check, dict):
                raise ValueError("Canary payload check entry must be an object.")
            stage = raw_check.get("stage")
            status = raw_check.get("status")
            details = raw_check.get("details")
            if not isinstance(stage, str) or not isinstance(status, str):
                raise ValueError("Canary payload check entry must include string stage/status.")
            if not isinstance(details, dict):
                raise ValueError("Canary payload check entry must include details object.")
            checks.append(
                StageCheck(
                    stage=stage,
                    status=status,
                    details={str(key): value for key, value in details.items()},
                )
            )
        stage_diagnostics = _checks_to_stage_diagnostics(checks)
        return {
            "variant_id": variant.variant_id,
            "description": variant.description,
            **payload,
            "stage_diagnostics": stage_diagnostics,
            "key_metrics": _key_metrics(stage_diagnostics),
        }
    except CanaryStageError as exc:
        stage_diagnostics = _checks_to_stage_diagnostics(exc.checks)
        return {
            "variant_id": variant.variant_id,
            "description": variant.description,
            "story_id": story_id,
            "source_type": variant.source_type,
            "target_language": variant.target_language,
            **_failure_payload(error=exc),
            "stage_diagnostics": stage_diagnostics,
            "key_metrics": _key_metrics(stage_diagnostics),
        }


def run_canary_matrix(
    *,
    variants: list[CanaryVariant],
    strict: bool,
    fixture_version: str,
) -> dict[str, object]:
    results = [_run_variant(variant=variant, strict=strict) for variant in variants]
    failed = sum(1 for result in results if result["status"] != "ok")
    passed = len(results) - failed
    return {
        "status": "ok" if failed == 0 else "failed",
        "fixture_version": fixture_version,
        "evaluated_at_utc": datetime.now(tz=UTC).isoformat(),
        "totals": {
            "variants": len(results),
            "passed": passed,
            "failed": failed,
        },
        "variants": results,
    }


def _write_matrix_output(*, output: str | None, payload: dict[str, object]) -> None:
    if output is None:
        return
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _emit_stage_failure(*, stage: str, error: Exception, checks: list[StageCheck]) -> None:
    raise CanaryStageError(stage=stage, error=error, checks=checks)


def run_canary(
    *,
    story_id: str,
    source_text: str,
    source_type: str,
    target_language: str,
    strict: bool,
) -> dict[str, object]:
    checks: list[StageCheck] = []
    try:
        artifact = ingest_story_text(
            IngestionRequest(
                source_type=source_type,
                source_text=source_text,
                idempotency_key=story_id,
            )
        )
        checks.append(
            StageCheck(
                stage="ingestion",
                status="ok",
                details={
                    "segments": len(artifact.segments),
                    "issues": len(artifact.issues),
                    "source_hash": artifact.source_hash,
                },
            )
        )
    except Exception as exc:
        _emit_stage_failure(stage="ingestion", error=exc, checks=checks)

    try:
        translated_segments, alignments, source_language = translate_segments(
            segments=artifact.segments,
            target_language=target_language,
        )
        validate_extraction_input(translated_segments)
        checks.append(
            StageCheck(
                stage="translation",
                status="ok",
                details={
                    "segments": len(translated_segments),
                    "alignments": len(alignments),
                    "source_language": source_language,
                },
            )
        )
    except Exception as exc:
        _emit_stage_failure(stage="translation", error=exc, checks=checks)

    try:
        events, entities = extract_events_and_entities(segments=translated_segments)
        validate_extraction_output(events)
        checks.append(
            StageCheck(
                stage="extraction",
                status="ok",
                details={"events": len(events), "entities": len(entities)},
            )
        )
    except Exception as exc:
        _emit_stage_failure(stage="extraction", error=exc, checks=checks)

    try:
        validate_beat_input(events)
        beats = detect_story_beats(events=events)
        validate_beat_output(beats)
        checks.append(
            StageCheck(
                stage="beat_detection",
                status="ok",
                details={"beats": len(beats), "stages": sorted({beat.stage for beat in beats})},
            )
        )
    except Exception as exc:
        _emit_stage_failure(stage="beat_detection", error=exc, checks=checks)

    try:
        validate_theme_input(beats)
        themes, arcs, conflicts, emotions = track_theme_arc_signals(beats=beats, entities=entities)
        validate_theme_output(themes)
        checks.append(
            StageCheck(
                stage="theme_tracking",
                status="ok",
                details={
                    "themes": len(themes),
                    "arcs": len(arcs),
                    "conflicts": len(conflicts),
                    "emotions": len(emotions),
                },
            )
        )
    except Exception as exc:
        _emit_stage_failure(stage="theme_tracking", error=exc, checks=checks)

    try:
        validate_timeline_input(events, beats)
        timeline = compose_timeline(events=events, beats=beats)
        validate_timeline_output(timeline.narrative_order)
        if not timeline.actual_time:
            raise ValueError("actual_time timeline lane is empty.")
        checks.append(
            StageCheck(
                stage="timeline",
                status="ok",
                details={
                    "actual_time_points": len(timeline.actual_time),
                    "narrative_points": len(timeline.narrative_order),
                },
            )
        )
    except Exception as exc:
        _emit_stage_failure(stage="timeline", error=exc, checks=checks)

    try:
        validate_insight_input(beats, themes)
        insights = generate_insights(beats=beats, themes=themes)
        validate_insight_output(insights)
        checks.append(
            StageCheck(
                stage="insights",
                status="ok",
                details={"insights": len(insights)},
            )
        )
    except Exception as exc:
        _emit_stage_failure(stage="insights", error=exc, checks=checks)

    try:
        quality_gate, _ = evaluate_quality_gate(
            segments=translated_segments,
            insights=insights,
            timeline_consistency=timeline.consistency_score,
        )
        if strict and not quality_gate.passed:
            raise ValueError(
                f"quality gate failed with reasons: {', '.join(quality_gate.reasons) or 'unknown'}"
            )
        dashboard = build_dashboard_read_model(
            document=StoryDocument(
                story_id=story_id,
                source_language=source_language,
                target_language=target_language,
                raw_segments=translated_segments,
                extracted_events=events,
                story_beats=beats,
                theme_signals=themes,
                entity_mentions=entities,
                timeline_points=timeline.narrative_order,
                insights=insights,
                quality_gate=quality_gate,
            ),
            arcs=arcs,
            conflicts=conflicts,
            emotions=emotions,
            timeline_actual=timeline.actual_time,
            timeline_narrative=timeline.narrative_order,
            timeline_conflicts=timeline.conflicts,
        )
        graph_svg = export_graph_svg(nodes=dashboard.graph_nodes, edges=dashboard.graph_edges)
        checks.append(
            StageCheck(
                stage="dashboard_projection",
                status="ok",
                details={
                    "graph_nodes": len(dashboard.graph_nodes),
                    "graph_edges": len(dashboard.graph_edges),
                    "graph_svg_length": len(graph_svg),
                },
            )
        )
    except Exception as exc:
        _emit_stage_failure(stage="dashboard_projection", error=exc, checks=checks)

    return {
        "status": "ok",
        "story_id": story_id,
        "source_type": source_type,
        "target_language": target_language,
        "checks": [asdict(check) for check in checks],
    }


def main(argv: list[str] | None = None) -> None:
    parsed = _parser().parse_args(argv)
    strict = bool(parsed.strict)
    if parsed.variant is not None or parsed.run_all_variants:
        if parsed.source_file is not None:
            raise SystemExit("--source-file is not supported with --variant/--run-all-variants.")
        catalog, fixture_version = _load_variant_catalog(parsed.variants_file)
        selected_variants = _select_variants(
            catalog=catalog,
            requested_ids=(
                [str(value) for value in parsed.variant] if parsed.variant is not None else None
            ),
            run_all_variants=bool(parsed.run_all_variants),
        )
        if not selected_variants:
            raise SystemExit("No canary variants selected.")
        payload = run_canary_matrix(
            variants=selected_variants,
            strict=strict,
            fixture_version=fixture_version,
        )
        _write_matrix_output(output=parsed.matrix_output, payload=payload)
        print(json.dumps(payload, indent=2))
        if payload["status"] != "ok":
            raise SystemExit(1)
        return

    source_text = _load_source(parsed.source_file, source_type=str(parsed.source_type))
    try:
        payload = run_canary(
            story_id=str(parsed.story_id),
            source_text=source_text,
            source_type=str(parsed.source_type),
            target_language=str(parsed.target_language),
            strict=strict,
        )
    except CanaryStageError as exc:
        payload = _failure_payload(error=exc)
        print(json.dumps(payload, indent=2))
        raise SystemExit(1)

    _write_matrix_output(output=parsed.matrix_output, payload=payload)
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
