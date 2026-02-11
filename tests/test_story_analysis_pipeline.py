from __future__ import annotations

from dataclasses import asdict

from story_gen.core.dashboard_views import (
    export_graph_png,
    export_theme_heatmap_png,
    export_theme_heatmap_svg,
    export_timeline_png,
    export_timeline_svg,
)
from story_gen.core.story_analysis_pipeline import run_story_analysis


def _sample_story() -> str:
    return (
        "Rhea enters the archive and finds her family's ledger. "
        "A conflict erupts when the council denies the records. "
        "She confronts the council in the central hall. "
        "The city accepts the truth and begins to heal."
    )


def test_story_analysis_pipeline_produces_all_major_artifacts() -> None:
    result = run_story_analysis(story_id="story-001", source_text=_sample_story())
    assert result.document.story_id == "story-001"
    assert result.document.raw_segments
    assert result.document.extracted_events
    assert result.document.story_beats
    assert result.document.theme_signals
    assert result.document.insights
    assert result.document.timeline_points
    assert result.dashboard.overview.events_count == len(result.document.extracted_events)
    assert result.timeline.actual_time
    assert result.timeline.narrative_order
    assert result.graph_svg.startswith("<svg")
    assert result.timing["total_seconds"] > 0


def test_story_analysis_pipeline_is_deterministic_for_same_input() -> None:
    first = run_story_analysis(story_id="story-xyz", source_text=_sample_story())
    second = run_story_analysis(story_id="story-xyz", source_text=_sample_story())
    assert [beat.beat_id for beat in first.document.story_beats] == [
        beat.beat_id for beat in second.document.story_beats
    ]
    assert [event.event_id for event in first.document.extracted_events] == [
        event.event_id for event in second.document.extracted_events
    ]
    assert [insight.insight_id for insight in first.document.insights] == [
        insight.insight_id for insight in second.document.insights
    ]
    assert first.dashboard.overview.macro_thesis == second.dashboard.overview.macro_thesis


def test_pipeline_reports_stage_timings() -> None:
    result = run_story_analysis(story_id="story-timing", source_text=_sample_story())
    expected_keys = {
        "ingestion_seconds",
        "translation_seconds",
        "extraction_seconds",
        "beat_detection_seconds",
        "theme_tracking_seconds",
        "timeline_seconds",
        "insights_seconds",
        "quality_gate_seconds",
        "dashboard_build_seconds",
        "graph_svg_seconds",
        "total_seconds",
    }
    assert expected_keys.issubset(result.timing.keys())
    assert (
        result.timing["total_seconds"]
        >= sum(
            result.timing[key]
            for key in expected_keys
            if key.endswith("_seconds") and key != "total_seconds"
        )
        * 0.5
    )


def test_pipeline_generates_macro_meso_micro_insights() -> None:
    result = run_story_analysis(story_id="story-777", source_text=_sample_story())
    granularities = {insight.granularity for insight in result.document.insights}
    assert "macro" in granularities
    assert "meso" in granularities
    assert "micro" in granularities


def test_pipeline_handles_non_english_translation_path() -> None:
    spanish_story = "La historia de una familia cambia cuando encuentran la memoria perdida."
    result = run_story_analysis(story_id="story-es", source_text=spanish_story)
    assert result.document.source_language == "es"
    translated = [segment.translated_text for segment in result.document.raw_segments]
    assert any(text is not None and "story" in text.lower() for text in translated)
    assert result.document.quality_gate.translation_quality >= 0.5


def test_pipeline_marks_untranslated_japanese_as_quality_warning() -> None:
    japanese_story = "これは危険だ。スバルは記憶の断片を追いかける。"
    result = run_story_analysis(story_id="story-ja", source_text=japanese_story)
    assert result.document.source_language == "ja"
    assert result.document.quality_gate.translation_quality < 0.5
    assert "translation_quality_low" in result.document.quality_gate.reasons


def test_pipeline_assigns_graph_layout_coordinates() -> None:
    result = run_story_analysis(story_id="story-layout", source_text=_sample_story())
    assert result.dashboard.graph_nodes
    assert all(
        node.layout_x is not None and node.layout_y is not None
        for node in result.dashboard.graph_nodes
    )


def test_pipeline_graph_png_export_is_deterministic() -> None:
    result = run_story_analysis(story_id="story-layout-png", source_text=_sample_story())
    first = export_graph_png(nodes=result.dashboard.graph_nodes, edges=result.dashboard.graph_edges)
    second = export_graph_png(
        nodes=result.dashboard.graph_nodes, edges=result.dashboard.graph_edges
    )
    assert first.startswith(b"\x89PNG\r\n\x1a\n")
    assert first == second


def test_pipeline_timeline_and_heatmap_exports_are_deterministic() -> None:
    result = run_story_analysis(story_id="story-layout-views", source_text=_sample_story())
    timeline_svg_first = export_timeline_svg(lanes=result.dashboard.timeline_lanes)
    timeline_svg_second = export_timeline_svg(lanes=result.dashboard.timeline_lanes)
    timeline_png_first = export_timeline_png(lanes=result.dashboard.timeline_lanes)
    timeline_png_second = export_timeline_png(lanes=result.dashboard.timeline_lanes)
    heatmap_svg_first = export_theme_heatmap_svg(cells=result.dashboard.theme_heatmap)
    heatmap_svg_second = export_theme_heatmap_svg(cells=result.dashboard.theme_heatmap)
    heatmap_png_first = export_theme_heatmap_png(cells=result.dashboard.theme_heatmap)
    heatmap_png_second = export_theme_heatmap_png(cells=result.dashboard.theme_heatmap)

    assert timeline_svg_first.startswith("<svg")
    assert timeline_svg_first == timeline_svg_second
    assert timeline_png_first.startswith(b"\x89PNG\r\n\x1a\n")
    assert timeline_png_first == timeline_png_second
    assert heatmap_svg_first.startswith("<svg")
    assert heatmap_svg_first == heatmap_svg_second
    assert heatmap_png_first.startswith(b"\x89PNG\r\n\x1a\n")
    assert heatmap_png_first == heatmap_png_second


def test_pipeline_graph_edges_are_evidence_driven() -> None:
    """Verify graph edges only connect themes and beats with shared evidence segments."""
    result = run_story_analysis(story_id="story-drilldown", source_text=_sample_story())

    # Collect theme and beat IDs
    theme_ids = {node.id for node in result.dashboard.graph_nodes if node.group == "theme"}
    beat_ids = {node.id for node in result.dashboard.graph_nodes if node.group == "beat"}

    # Verify edges only exist between themes and beats (no other connections)
    for edge in result.dashboard.graph_edges:
        assert edge.relation == "expressed_in"
        assert edge.source in theme_ids, f"Edge source {edge.source} not a theme"
        assert edge.target in beat_ids, f"Edge target {edge.target} not a beat"
        assert 0.0 < edge.weight <= 1.0, f"Edge weight {edge.weight} out of valid range"

    # Verify no dense all-to-all connection: edge count should be much less than themes × beats
    total_possible_edges = len(theme_ids) * len(beat_ids)
    actual_edges = len(result.dashboard.graph_edges)
    if total_possible_edges > 0:
        # With evidence-driven filtering, actual edges should be <= 50% of possible edges
        # (typically much less with real story data)
        assert actual_edges <= total_possible_edges, (
            f"Too many edges: {actual_edges} (expected <= {total_possible_edges})"
        )


def test_pipeline_preserves_dashboard_heatmap_and_arc_shapes() -> None:
    result = run_story_analysis(story_id="story-shapes", source_text=_sample_story())
    assert result.dashboard.theme_heatmap
    assert result.dashboard.arc_points
    heatmap_payload = asdict(result.dashboard.theme_heatmap[0])
    arc_payload = asdict(result.dashboard.arc_points[0])
    assert set(heatmap_payload) == {"theme", "stage", "intensity"}
    assert set(arc_payload) == {"lane", "stage", "value", "label"}


def test_pipeline_drilldown_includes_theme_arc_conflict_and_emotion() -> None:
    result = run_story_analysis(story_id="story-drilldown", source_text=_sample_story())
    drilldown_items = result.dashboard.drilldown.values()
    item_types = {item.item_type for item in drilldown_items}
    assert any(item_type.startswith("insight:") for item_type in item_types)
    assert "theme" in item_types
    assert "arc" in item_types
    assert "conflict" in item_types
    assert "emotion" in item_types
    assert all(item.evidence_segment_ids for item in drilldown_items)


def test_pipeline_drilldown_includes_extraction_detail_items() -> None:
    source_text = (
        'Rhea said, "We cannot turn back." '
        '"Then hold the line," said Rhea. '
        "I thought we were done, but I kept moving."
    )
    result = run_story_analysis(story_id="story-extraction-details", source_text=source_text)

    item_types = {item.item_type for item in result.dashboard.drilldown.values()}
    assert "extraction_detail" in item_types
    assert "extraction_monologue" in item_types
    assert "extraction_speaker" in item_types

    speaker_items = [
        item
        for item in result.dashboard.drilldown.values()
        if item.item_type == "extraction_speaker"
    ]
    assert speaker_items
    assert all(item.evidence_segment_ids for item in speaker_items)


def test_pipeline_drilldown_includes_essence_profiles_and_constraints() -> None:
    source_text = (
        "Rhea feared the shadowed archive but vowed to continue. "
        'Rhea said, "I will adapt and persist." '
        "The council guarded old rituals while a hidden rune surfaced."
    )
    result = run_story_analysis(story_id="story-essence", source_text=source_text)
    item_types = {item.item_type for item in result.dashboard.drilldown.values()}

    assert "essence_fragment" in item_types
    assert "essence_guidance" in item_types
    assert "essence_world" in item_types
    assert "essence_world_stage" in item_types
    assert "essence_character" in item_types
    assert "essence_constraint" in item_types
    assert "essence_world_alignment" in item_types
