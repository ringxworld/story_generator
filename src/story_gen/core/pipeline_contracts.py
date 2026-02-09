"""Validation helpers that enforce stage contracts and deterministic ordering."""

from __future__ import annotations

from dataclasses import dataclass

from story_gen.core.story_schema import (
    ExtractedEvent,
    Insight,
    RawSegment,
    StoryBeat,
    ThemeSignal,
    TimelinePoint,
)


@dataclass(frozen=True)
class PipelineStageContract:
    """Track one pipeline stage input/output contract boundary."""

    stage_id: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    validator_functions: tuple[str, ...]
    description: str


PIPELINE_STAGE_CONTRACTS: tuple[PipelineStageContract, ...] = (
    PipelineStageContract(
        stage_id="ingestion.translation",
        inputs=("RawSegment[]",),
        outputs=("RawSegment[]", "SegmentAlignment[]"),
        validator_functions=("validate_extraction_input",),
        description="Normalize/transcode source segments before extraction.",
    ),
    PipelineStageContract(
        stage_id="extraction.events_entities",
        inputs=("RawSegment[]",),
        outputs=("ExtractedEvent[]", "EntityMention[]"),
        validator_functions=("validate_extraction_input", "validate_extraction_output"),
        description="Extract event and entity records from normalized segments.",
    ),
    PipelineStageContract(
        stage_id="narrative.beat_detection",
        inputs=("ExtractedEvent[]",),
        outputs=("StoryBeat[]",),
        validator_functions=("validate_beat_input", "validate_beat_output"),
        description="Map events into ordered setup/escalation/climax/resolution beats.",
    ),
    PipelineStageContract(
        stage_id="themes.arcs_conflicts",
        inputs=("StoryBeat[]",),
        outputs=("ThemeSignal[]", "ArcSignal[]", "ConflictShift[]", "EmotionSignal[]"),
        validator_functions=("validate_theme_input", "validate_theme_output"),
        description="Track theme intensity and narrative arc signals by stage.",
    ),
    PipelineStageContract(
        stage_id="timeline.compose",
        inputs=("ExtractedEvent[]", "StoryBeat[]"),
        outputs=("TimelinePoint[]",),
        validator_functions=("validate_timeline_input", "validate_timeline_output"),
        description="Compose chronology and narrative-order timeline views.",
    ),
    PipelineStageContract(
        stage_id="insights.generate",
        inputs=("StoryBeat[]", "ThemeSignal[]"),
        outputs=("Insight[]",),
        validator_functions=("validate_insight_input", "validate_insight_output"),
        description="Generate macro/meso/micro insights with evidence links.",
    ),
)


def registered_pipeline_stage_contracts() -> tuple[PipelineStageContract, ...]:
    """Return the tracked stage-level pipeline contract registry."""
    return PIPELINE_STAGE_CONTRACTS


def _assert_order(values: list[int], *, label: str) -> None:
    if values != sorted(values):
        raise ValueError(f"{label} must be sorted in ascending order.")
    expected = list(range(1, len(values) + 1))
    if values != expected:
        raise ValueError(f"{label} must be a contiguous 1..N sequence.")


def validate_extraction_input(segments: list[RawSegment]) -> None:
    """Validate segment inputs for extraction."""
    if not segments:
        raise ValueError("At least one segment is required.")
    _assert_order([segment.segment_index for segment in segments], label="segment_index")
    for segment in segments:
        if segment.char_end <= segment.char_start:
            raise ValueError("Segment char_end must be > char_start.")


def validate_extraction_output(events: list[ExtractedEvent]) -> None:
    """Validate extracted events output contract."""
    if not events:
        raise ValueError("Event extraction must produce at least one event.")
    _assert_order([event.narrative_order for event in events], label="event narrative_order")
    for event in events:
        if not event.provenance.source_segment_ids:
            raise ValueError("Events require provenance source_segment_ids.")


def validate_beat_input(events: list[ExtractedEvent]) -> None:
    """Validate beat detection inputs."""
    validate_extraction_output(events)


def validate_beat_output(beats: list[StoryBeat]) -> None:
    """Validate beat stage contract."""
    if not beats:
        raise ValueError("Beat stage must produce at least one beat.")
    _assert_order([beat.order_index for beat in beats], label="beat order_index")
    for beat in beats:
        if not beat.evidence_segment_ids:
            raise ValueError("Beat records require evidence segments.")


def validate_theme_input(beats: list[StoryBeat]) -> None:
    """Validate theme tracking inputs."""
    validate_beat_output(beats)


def validate_theme_output(themes: list[ThemeSignal]) -> None:
    """Validate theme tracking output contract."""
    if not themes:
        raise ValueError("Theme stage must produce at least one signal.")
    for signal in themes:
        if not signal.evidence_segment_ids:
            raise ValueError("Theme signals require evidence.")


def validate_timeline_input(events: list[ExtractedEvent], beats: list[StoryBeat]) -> None:
    """Validate timeline composer inputs."""
    validate_extraction_output(events)
    validate_beat_output(beats)


def validate_timeline_output(points: list[TimelinePoint]) -> None:
    """Validate timeline composition output."""
    if not points:
        raise ValueError("Timeline stage must produce at least one point.")
    _assert_order([point.narrative_order for point in points], label="timeline narrative_order")


def validate_insight_input(beats: list[StoryBeat], themes: list[ThemeSignal]) -> None:
    """Validate insight generation inputs."""
    validate_beat_output(beats)
    validate_theme_output(themes)


def validate_insight_output(insights: list[Insight]) -> None:
    """Validate insight generation outputs."""
    if not insights:
        raise ValueError("Insight stage must produce at least one insight.")
    for insight in insights:
        if not insight.evidence_segment_ids:
            raise ValueError("Insight records require evidence links.")
        if insight.confidence.score <= 0.0:
            raise ValueError("Insight confidence must be positive.")
