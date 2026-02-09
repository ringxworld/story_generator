"""Pipeline canary command for end-to-end stage validation."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

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


DEFAULT_SOURCE_TEXT = (
    "[00:01] Narrator: Rhea enters the archive and finds her family's ledger.\n"
    "[00:40] Council: The council denies the records and tension rises.\n"
    "[01:10] Rhea: She confronts the council in the central hall.\n"
    "[01:42] Narrator: The city accepts the truth and begins to heal.\n"
)


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


def _emit_failure(*, stage: str, error: Exception, checks: list[StageCheck]) -> None:
    payload = {
        "status": "failed",
        "failed_stage": stage,
        "error": str(error),
        "checks": [asdict(check) for check in checks],
    }
    print(json.dumps(payload, indent=2))
    raise SystemExit(1)


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
        _emit_failure(stage="ingestion", error=exc, checks=checks)

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
        _emit_failure(stage="translation", error=exc, checks=checks)

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
        _emit_failure(stage="extraction", error=exc, checks=checks)

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
        _emit_failure(stage="beat_detection", error=exc, checks=checks)

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
        _emit_failure(stage="theme_tracking", error=exc, checks=checks)

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
        _emit_failure(stage="timeline", error=exc, checks=checks)

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
        _emit_failure(stage="insights", error=exc, checks=checks)

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
        _emit_failure(stage="dashboard_projection", error=exc, checks=checks)

    return {
        "status": "ok",
        "story_id": story_id,
        "source_type": source_type,
        "target_language": target_language,
        "checks": [asdict(check) for check in checks],
    }


def main(argv: list[str] | None = None) -> None:
    parsed = _parser().parse_args(argv)
    source_text = _load_source(parsed.source_file, source_type=str(parsed.source_type))
    payload = run_canary(
        story_id=str(parsed.story_id),
        source_text=source_text,
        source_type=str(parsed.source_type),
        target_language=str(parsed.target_language),
        strict=bool(parsed.strict),
    )
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
