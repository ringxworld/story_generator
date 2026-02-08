"""End-to-end story intelligence pipeline orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from story_gen.core.dashboard_views import (
    DashboardReadModel,
    build_dashboard_read_model,
    export_graph_svg,
)
from story_gen.core.insight_engine import generate_insights
from story_gen.core.language_translation import SegmentAlignment, translate_segments
from story_gen.core.narrative_analysis import detect_story_beats
from story_gen.core.quality_evaluation import EvaluationMetrics, evaluate_quality_gate
from story_gen.core.story_extraction import extract_events_and_entities
from story_gen.core.story_ingestion import IngestionRequest, ingest_story_text
from story_gen.core.story_schema import StoryDocument
from story_gen.core.theme_arc_tracking import (
    ArcSignal,
    ConflictShift,
    EmotionSignal,
    track_theme_arc_signals,
)
from story_gen.core.timeline_composer import ComposedTimeline, compose_timeline


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
    graph_svg: str


def run_story_analysis(
    *,
    story_id: str,
    source_text: str,
    source_type: str = "text",
    target_language: str = "en",
) -> StoryAnalysisResult:
    """Run complete deterministic story analysis pipeline."""
    artifact = ingest_story_text(
        IngestionRequest(
            source_type=source_type,
            source_text=source_text,
            idempotency_key=story_id,
        )
    )
    translated_segments, alignments, source_language = translate_segments(
        segments=artifact.segments,
        target_language=target_language,
    )
    events, entities = extract_events_and_entities(segments=translated_segments)
    beats = detect_story_beats(events=events)
    themes, arcs, conflicts, emotions = track_theme_arc_signals(beats=beats, entities=entities)
    timeline = compose_timeline(events=events, beats=beats)
    insights = generate_insights(beats=beats, themes=themes)
    quality_gate, evaluation = evaluate_quality_gate(
        segments=translated_segments,
        insights=insights,
    )
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
    dashboard = build_dashboard_read_model(
        document=document,
        arcs=arcs,
        conflicts=conflicts,
        emotions=emotions,
        timeline_actual=timeline.actual_time,
        timeline_narrative=timeline.narrative_order,
    )
    graph_svg = export_graph_svg(nodes=dashboard.graph_nodes, edges=dashboard.graph_edges)
    return StoryAnalysisResult(
        document=document,
        dashboard=dashboard,
        timeline=timeline,
        alignments=alignments,
        arcs=arcs,
        conflicts=conflicts,
        emotions=emotions,
        evaluation=evaluation,
        graph_svg=graph_svg,
    )
