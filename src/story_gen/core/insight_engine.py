"""Multi-granularity insight generation."""

from __future__ import annotations

import os
import re
from typing import Final

from story_gen.core.pipeline_contracts import validate_insight_input, validate_insight_output
from story_gen.core.story_schema import (
    STORY_STAGE_ORDER,
    ConfidenceScore,
    Insight,
    ProvenanceRecord,
    StoryBeat,
    StoryStage,
    ThemeSignal,
    stable_id,
)

_WORD_TOKEN = re.compile(r"[A-Za-z']+")
_STYLE_TEMPLATES: Final[dict[str, str]] = {
    "plain.v1": "{content}",
    "dashboard.v1": "Signal: {content}",
    "export.v1": "Evidence-backed insight: {content}",
}


def generate_insights(*, beats: list[StoryBeat], themes: list[ThemeSignal]) -> list[Insight]:
    """Generate macro, meso, and micro insights with evidence links."""
    validate_insight_input(beats, themes)
    insights: list[Insight] = []
    style_template = _resolve_style_template()

    stage_groups: dict[StoryStage, list[StoryBeat]] = {stage: [] for stage in STORY_STAGE_ORDER}
    for beat in beats:
        stage_groups[beat.stage].append(beat)

    macro_evidence = sorted({segment for beat in beats for segment in beat.evidence_segment_ids})
    macro_content = " ".join(beat.summary for beat in beats[:8])
    if not macro_content:
        macro_content = "No summary available."
    macro_confidence = _macro_confidence(beats=beats, themes=themes, evidence=macro_evidence)
    insights.append(
        Insight(
            insight_id=stable_id(prefix="ins", text=f"macro:{macro_content}"),
            granularity="macro",
            title="Story Thesis",
            content=_render_content(
                template=style_template,
                granularity="macro",
                content=macro_content,
            ),
            stage=None,
            beat_id=None,
            evidence_segment_ids=macro_evidence[:32] or [beats[0].evidence_segment_ids[0]],
            confidence=ConfidenceScore(method="insight.calibrated.v2", score=macro_confidence),
            provenance=ProvenanceRecord(
                source_segment_ids=macro_evidence[:32],
                generator="insight_engine",
            ),
        )
    )

    for stage in STORY_STAGE_ORDER:
        stage_beats = stage_groups[stage]
        if not stage_beats:
            continue
        stage_summary = " ".join(beat.summary for beat in stage_beats[:3])
        evidence = sorted(
            {segment for beat in stage_beats for segment in beat.evidence_segment_ids}
        )
        meso_confidence = _meso_confidence(
            stage=stage,
            stage_beats=stage_beats,
            themes=themes,
            evidence=evidence,
        )
        insights.append(
            Insight(
                insight_id=stable_id(prefix="ins", text=f"meso:{stage}:{stage_summary}"),
                granularity="meso",
                title=f"{stage.title()} Takeaway",
                content=_render_content(
                    template=style_template,
                    granularity="meso",
                    content=stage_summary,
                ),
                stage=stage,
                beat_id=None,
                evidence_segment_ids=evidence or [stage_beats[0].evidence_segment_ids[0]],
                confidence=ConfidenceScore(method="insight.calibrated.v2", score=meso_confidence),
                provenance=ProvenanceRecord(
                    source_segment_ids=evidence,
                    generator="insight_engine",
                ),
            )
        )

    for beat in beats:
        micro_confidence = _micro_confidence(beat=beat, themes=themes)
        insights.append(
            Insight(
                insight_id=stable_id(prefix="ins", text=f"micro:{beat.beat_id}"),
                granularity="micro",
                title=f"Beat {beat.order_index}",
                content=_render_content(
                    template=style_template,
                    granularity="micro",
                    content=beat.summary,
                ),
                stage=beat.stage,
                beat_id=beat.beat_id,
                evidence_segment_ids=beat.evidence_segment_ids,
                confidence=ConfidenceScore(method="insight.calibrated.v2", score=micro_confidence),
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


def _resolve_style_template() -> str:
    raw = os.environ.get("STORY_GEN_INSIGHT_STYLE_TEMPLATE", "plain.v1").strip().lower()
    if raw in _STYLE_TEMPLATES:
        return raw
    return "plain.v1"


def _render_content(*, template: str, granularity: str, content: str) -> str:
    rendered = _STYLE_TEMPLATES.get(template, "{content}").format(content=content)
    if template == "dashboard.v1":
        return f"{granularity.upper()} {rendered}"
    return rendered


def _macro_confidence(
    *,
    beats: list[StoryBeat],
    themes: list[ThemeSignal],
    evidence: list[str],
) -> float:
    evidence_coverage = len(set(evidence)) / max(1, len(beats))
    theme_strength = sum(theme.strength for theme in themes) / max(1, len(themes))
    value = 0.62 + min(0.2, evidence_coverage * 0.12) + min(0.14, theme_strength * 0.18)
    return _bounded(value)


def _meso_confidence(
    *,
    stage: StoryStage,
    stage_beats: list[StoryBeat],
    themes: list[ThemeSignal],
    evidence: list[str],
) -> float:
    stage_theme_strength = max(
        (theme.strength for theme in themes if theme.stage == stage), default=0.0
    )
    stage_signal = min(1.0, len(stage_beats) / 2)
    evidence_density = len(set(evidence)) / max(1, len(stage_beats))
    value = (
        0.58
        + min(0.16, stage_signal * 0.13)
        + min(0.14, stage_theme_strength * 0.18)
        + min(0.1, evidence_density * 0.08)
    )
    return _bounded(value)


def _micro_confidence(*, beat: StoryBeat, themes: list[ThemeSignal]) -> float:
    stage_themes = [theme for theme in themes if theme.stage == beat.stage]
    stage_theme_strength = (
        sum(theme.strength for theme in stage_themes) / max(1, len(stage_themes))
        if stage_themes
        else 0.0
    )
    lexical_density = _lexical_density(beat.summary)
    value = 0.56 + min(0.2, beat.confidence.score * 0.2) + min(0.14, stage_theme_strength * 0.18)
    value += min(0.08, lexical_density * 0.1)
    return _bounded(value)


def _lexical_density(text: str) -> float:
    tokens = [token.lower() for token in _WORD_TOKEN.findall(text)]
    if not tokens:
        return 0.0
    return len(set(tokens)) / len(tokens)


def _bounded(value: float) -> float:
    return round(min(0.98, max(0.0, value)), 3)
