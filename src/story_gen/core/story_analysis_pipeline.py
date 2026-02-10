"""End-to-end story intelligence pipeline orchestration."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from story_gen.core.dashboard_views import (
    DashboardReadModel,
    build_dashboard_read_model,
    export_graph_svg,
)
from story_gen.core.insight_engine import generate_insights
from story_gen.core.language_translation import (
    SegmentAlignment,
    TranslationDiagnostics,
    translate_segments_with_diagnostics,
)
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
from story_gen.core.quality_evaluation import EvaluationMetrics, evaluate_quality_gate
from story_gen.core.story_extraction import (
    ExtractionDiagnostics,
    extract_events_and_entities_with_diagnostics,
)
from story_gen.core.story_ingestion import IngestionArtifact, IngestionRequest, ingest_story_text
from story_gen.core.story_schema import StoryDocument
from story_gen.core.theme_arc_tracking import (
    ArcSignal,
    ConflictShift,
    EmotionSignal,
    track_theme_arc_signals,
)
from story_gen.core.timeline_composer import ComposedTimeline, compose_timeline

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StoryAnalysisResult:
    """Combined output from all analysis stages."""

    document: StoryDocument
    dashboard: DashboardReadModel
    timeline: ComposedTimeline
    alignments: list[SegmentAlignment]
    arcs: list[ArcSignal]
    conflicts: list[ConflictShift]
    emotions: list[EmotionSignal]
    evaluation: EvaluationMetrics
    translation_diagnostics: TranslationDiagnostics
    extraction_diagnostics: ExtractionDiagnostics
    graph_svg: str
    timing: dict[str, float]


def run_story_analysis(
    *,
    story_id: str,
    source_text: str,
    source_type: str = "text",
    target_language: str = "en",
    ingestion_artifact: IngestionArtifact | None = None,
) -> StoryAnalysisResult:
    """Run complete deterministic story analysis pipeline."""
    timings: dict[str, float] = {}
    started = time.perf_counter()
    logger.info(
        "analysis.start story_id=%s source_type=%s target_language=%s",
        story_id,
        source_type,
        target_language,
    )
    step_start = time.perf_counter()
    artifact = ingestion_artifact or ingest_story_text(
        IngestionRequest(
            source_type=source_type,
            source_text=source_text,
            idempotency_key=story_id,
        )
    )
    timings["ingestion_seconds"] = time.perf_counter() - step_start
    step_start = time.perf_counter()
    translated_segments, alignments, source_language, translation_diagnostics = (
        translate_segments_with_diagnostics(
            segments=artifact.segments,
            target_language=target_language,
        )
    )
    timings["translation_seconds"] = time.perf_counter() - step_start
    validate_extraction_input(translated_segments)
    logger.info(
        "analysis.translation story_id=%s segments=%s source_language=%s",
        story_id,
        len(translated_segments),
        source_language,
    )
    step_start = time.perf_counter()
    events, entities, extraction_diagnostics = extract_events_and_entities_with_diagnostics(
        segments=translated_segments
    )
    timings["extraction_seconds"] = time.perf_counter() - step_start
    validate_extraction_output(events)
    validate_beat_input(events)
    step_start = time.perf_counter()
    beats = detect_story_beats(events=events)
    timings["beat_detection_seconds"] = time.perf_counter() - step_start
    validate_beat_output(beats)
    validate_theme_input(beats)
    step_start = time.perf_counter()
    themes, arcs, conflicts, emotions = track_theme_arc_signals(beats=beats, entities=entities)
    timings["theme_tracking_seconds"] = time.perf_counter() - step_start
    validate_theme_output(themes)
    validate_timeline_input(events, beats)
    step_start = time.perf_counter()
    timeline = compose_timeline(events=events, beats=beats)
    timings["timeline_seconds"] = time.perf_counter() - step_start
    validate_timeline_output(timeline.narrative_order)
    validate_insight_input(beats, themes)
    step_start = time.perf_counter()
    insights = generate_insights(beats=beats, themes=themes)
    timings["insights_seconds"] = time.perf_counter() - step_start
    validate_insight_output(insights)
    step_start = time.perf_counter()
    quality_gate, evaluation = evaluate_quality_gate(
        segments=translated_segments,
        insights=insights,
        timeline_consistency=timeline.consistency_score,
    )
    timings["quality_gate_seconds"] = time.perf_counter() - step_start
    document = StoryDocument(
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
    )
    step_start = time.perf_counter()
    dashboard = build_dashboard_read_model(
        document=document,
        arcs=arcs,
        conflicts=conflicts,
        emotions=emotions,
        timeline_actual=timeline.actual_time,
        timeline_narrative=timeline.narrative_order,
        timeline_conflicts=timeline.conflicts,
    )
    timings["dashboard_build_seconds"] = time.perf_counter() - step_start
    step_start = time.perf_counter()
    graph_svg = export_graph_svg(nodes=dashboard.graph_nodes, edges=dashboard.graph_edges)
    timings["graph_svg_seconds"] = time.perf_counter() - step_start
    timings["total_seconds"] = time.perf_counter() - started
    logger.info(
        "analysis.complete story_id=%s events=%s beats=%s themes=%s insights=%s quality_passed=%s",
        story_id,
        len(events),
        len(beats),
        len(themes),
        len(insights),
        document.quality_gate.passed,
    )
    return StoryAnalysisResult(
        document=document,
        dashboard=dashboard,
        timeline=timeline,
        alignments=alignments,
        arcs=arcs,
        conflicts=conflicts,
        emotions=emotions,
        evaluation=evaluation,
        translation_diagnostics=translation_diagnostics,
        extraction_diagnostics=extraction_diagnostics,
        graph_svg=graph_svg,
        timing=timings,
    )
