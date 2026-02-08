from __future__ import annotations

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

