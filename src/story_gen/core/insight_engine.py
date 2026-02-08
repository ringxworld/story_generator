"""Multi-granularity insight generation."""

from __future__ import annotations

from story_gen.core.pipeline_contracts import validate_insight_input, validate_insight_output
from story_gen.core.story_schema import (
    ConfidenceScore,
    Insight,
    ProvenanceRecord,
    StoryBeat,
    ThemeSignal,
    stable_id,
)


def generate_insights(*, beats: list[StoryBeat], themes: list[ThemeSignal]) -> list[Insight]:
    """Generate macro, meso, and micro insights with evidence links."""
    validate_insight_input(beats, themes)
    insights: list[Insight] = []

    stage_groups: dict[str, list[StoryBeat]] = {
        "setup": [],
        "escalation": [],
        "climax": [],
        "resolution": [],
    }
    for beat in beats:
        stage_groups[beat.stage].append(beat)

    macro_evidence = sorted({segment for beat in beats for segment in beat.evidence_segment_ids})
    macro_content = " ".join(beat.summary for beat in beats[:8])
    if not macro_content:
        macro_content = "No summary available."
    insights.append(
        Insight(
            insight_id=stable_id(prefix="ins", text=f"macro:{macro_content}"),
            granularity="macro",
            title="Story Thesis",
            content=macro_content,
            stage=None,
            beat_id=None,
            evidence_segment_ids=macro_evidence[:32] or [beats[0].evidence_segment_ids[0]],
            confidence=ConfidenceScore(method="insight.rule.v1", score=0.72),
            provenance=ProvenanceRecord(
                source_segment_ids=macro_evidence[:32],
                generator="insight_engine",
            ),
        )
    )

    for stage in ("setup", "escalation", "climax", "resolution"):
        stage_beats = stage_groups[stage]
        if not stage_beats:
            continue
        stage_summary = " ".join(beat.summary for beat in stage_beats[:3])
        evidence = sorted(
            {segment for beat in stage_beats for segment in beat.evidence_segment_ids}
        )
        insights.append(
            Insight(
                insight_id=stable_id(prefix="ins", text=f"meso:{stage}:{stage_summary}"),
                granularity="meso",
                title=f"{stage.title()} Takeaway",
                content=stage_summary,
                stage=stage,
                beat_id=None,
                evidence_segment_ids=evidence or [stage_beats[0].evidence_segment_ids[0]],
                confidence=ConfidenceScore(method="insight.rule.v1", score=0.7),
                provenance=ProvenanceRecord(
                    source_segment_ids=evidence,
                    generator="insight_engine",
                ),
            )
        )

    for beat in beats:
        insights.append(
            Insight(
                insight_id=stable_id(prefix="ins", text=f"micro:{beat.beat_id}"),
                granularity="micro",
                title=f"Beat {beat.order_index}",
                content=beat.summary,
                stage=beat.stage,
                beat_id=beat.beat_id,
                evidence_segment_ids=beat.evidence_segment_ids,
                confidence=ConfidenceScore(method="insight.rule.v1", score=0.68),
                provenance=ProvenanceRecord(
                    source_segment_ids=beat.evidence_segment_ids,
                    generator="insight_engine",
                ),
            )
        )

    _apply_theme_boost(insights=insights, themes=themes)
    validate_insight_output(insights)
    return insights


def _apply_theme_boost(*, insights: list[Insight], themes: list[ThemeSignal]) -> None:
    theme_strength = sum(theme.strength for theme in themes) / max(len(themes), 1)
    boost = min(0.15, round(theme_strength * 0.2, 3))
    for index, insight in enumerate(insights):
        updated = min(1.0, round(insight.confidence.score + boost, 3))
        insights[index] = insight.model_copy(
            update={
                "confidence": ConfidenceScore(
                    method=insight.confidence.method,
                    score=updated,
                )
            }
        )
