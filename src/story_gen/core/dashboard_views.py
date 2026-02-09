"""Dashboard read model projections from canonical story analysis artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape

from story_gen.core.story_schema import (
    Insight,
    StoryDocument,
    StoryStage,
    ThemeSignal,
    TimelinePoint,
)
from story_gen.core.theme_arc_tracking import ArcSignal, ConflictShift, EmotionSignal


@dataclass(frozen=True)
class DashboardOverviewCard:
    """Top-level dashboard summary card."""

    title: str
    macro_thesis: str
    confidence_floor: float
    quality_passed: bool
    events_count: int
    beats_count: int
    themes_count: int


@dataclass(frozen=True)
class TimelineLaneView:
    """Timeline lane projection."""

    lane: str
    items: list[dict[str, str | int | None]]


@dataclass(frozen=True)
class ThemeHeatmapCell:
    """Heatmap cell for one theme/stage pair."""

    theme: str
    stage: StoryStage
    intensity: float


@dataclass(frozen=True)
class ArcChartPoint:
    """Arc chart point for character/conflict/emotion panels."""

    lane: str
    stage: StoryStage
    value: float
    label: str


@dataclass(frozen=True)
class DrilldownPanelView:
    """Drilldown projection for one selected id."""

    item_id: str
    item_type: str
    title: str
    content: str
    evidence_segment_ids: list[str]


@dataclass(frozen=True)
class GraphNode:
    """Graph node used by interactive graph views."""

    id: str
    label: str
    group: str
    stage: StoryStage | None
    layout_x: int | None = None
    layout_y: int | None = None


@dataclass(frozen=True)
class GraphEdge:
    """Graph edge used by interactive graph views."""

    source: str
    target: str
    relation: str
    weight: float


@dataclass(frozen=True)
class DashboardReadModel:
    """Composed dashboard projection returned by API layer."""

    overview: DashboardOverviewCard
    timeline_lanes: list[TimelineLaneView]
    theme_heatmap: list[ThemeHeatmapCell]
    arc_points: list[ArcChartPoint]
    drilldown: dict[str, DrilldownPanelView]
    graph_nodes: list[GraphNode]
    graph_edges: list[GraphEdge]


def build_dashboard_read_model(
    *,
    document: StoryDocument,
    arcs: list[ArcSignal],
    conflicts: list[ConflictShift],
    emotions: list[EmotionSignal],
    timeline_actual: list[TimelinePoint],
    timeline_narrative: list[TimelinePoint],
) -> DashboardReadModel:
    """Project canonical artifacts into dashboard-oriented read models."""
    overview = _build_overview(document)
    timeline_lanes = _build_timeline_lanes(timeline_actual, timeline_narrative)
    theme_heatmap = _build_theme_heatmap(document.theme_signals)
    arc_points = _build_arc_points(arcs, conflicts, emotions)
    drilldown = _build_drilldown(document.insights)
    graph_nodes, graph_edges = _build_graph(document, arcs)
    return DashboardReadModel(
        overview=overview,
        timeline_lanes=timeline_lanes,
        theme_heatmap=theme_heatmap,
        arc_points=arc_points,
        drilldown=drilldown,
        graph_nodes=graph_nodes,
        graph_edges=graph_edges,
    )


def export_graph_svg(*, nodes: list[GraphNode], edges: list[GraphEdge]) -> str:
    """Export graph projection to deterministic SVG text."""
    width = 900
    height = 520
    x_step = max(100, width // max(len(nodes), 1))
    node_coords: dict[str, tuple[int, int]] = {}
    circles: list[str] = []
    labels: list[str] = []

    for index, node in enumerate(nodes, start=1):
        x = node.layout_x if node.layout_x is not None else min(width - 40, 40 + index * x_step)
        y = (
            node.layout_y
            if node.layout_y is not None
            else 120
            if node.group == "theme"
            else 260
            if node.group == "beat"
            else 390
        )
        node_coords[node.id] = (x, y)
        circles.append(
            f'<circle cx="{x}" cy="{y}" r="16" fill="#2E5E4E" stroke="#173629" stroke-width="2" />'
        )
        labels.append(
            f'<text x="{x}" y="{y + 32}" text-anchor="middle" fill="#10231C" font-size="12">{escape(node.label)}</text>'
        )

    lines: list[str] = []
    for edge in edges:
        source = node_coords.get(edge.source)
        target = node_coords.get(edge.target)
        if source is None or target is None:
            continue
        lines.append(
            f'<line x1="{source[0]}" y1="{source[1]}" x2="{target[0]}" y2="{target[1]}" stroke="#5C8B7A" stroke-width="1.5" />'
        )

    body = "\n".join(lines + circles + labels)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}"><rect width="100%" height="100%" fill="#EEF5F2" />{body}</svg>'
    )


def _build_overview(document: StoryDocument) -> DashboardOverviewCard:
    macro = next((insight for insight in document.insights if insight.granularity == "macro"), None)
    macro_text = macro.content if macro is not None else "No macro insight available."
    return DashboardOverviewCard(
        title="Story Intelligence Overview",
        macro_thesis=macro_text,
        confidence_floor=document.quality_gate.confidence_floor,
        quality_passed=document.quality_gate.passed,
        events_count=len(document.extracted_events),
        beats_count=len(document.story_beats),
        themes_count=len(document.theme_signals),
    )


def _build_timeline_lanes(
    actual: list[TimelinePoint], narrative: list[TimelinePoint]
) -> list[TimelineLaneView]:
    actual_items = _project_timeline_items(actual)
    narrative_items = _project_timeline_items(narrative)
    return [
        TimelineLaneView(
            lane="actual_time",
            items=actual_items,
        ),
        TimelineLaneView(
            lane="narrative_order",
            items=narrative_items,
        ),
    ]


def _project_timeline_items(points: list[TimelinePoint]) -> list[dict[str, str | int | None]]:
    return [
        {
            "id": point.point_id,
            "label": point.label,
            "order": point.narrative_order,
            "time": point.actual_time_utc,
        }
        for point in points
    ]


def _build_theme_heatmap(themes: list[ThemeSignal]) -> list[ThemeHeatmapCell]:
    return [
        ThemeHeatmapCell(theme=signal.label, stage=signal.stage, intensity=signal.strength)
        for signal in sorted(
            themes, key=lambda signal: (signal.label, signal.stage, signal.theme_id)
        )
    ]


def _build_arc_points(
    arcs: list[ArcSignal], conflicts: list[ConflictShift], emotions: list[EmotionSignal]
) -> list[ArcChartPoint]:
    points: list[ArcChartPoint] = []
    for arc in arcs:
        points.append(
            ArcChartPoint(
                lane=f"character:{arc.entity_name}",
                stage=arc.stage,
                value=arc.delta,
                label=arc.state,
            )
        )
    for conflict in conflicts:
        points.append(
            ArcChartPoint(
                lane="conflict",
                stage=conflict.stage,
                value=conflict.intensity_delta,
                label=f"{conflict.from_state}->{conflict.to_state}",
            )
        )
    for emotion in emotions:
        points.append(
            ArcChartPoint(
                lane="emotion",
                stage=emotion.stage,
                value=emotion.score,
                label=emotion.tone,
            )
        )
    return points


def _build_drilldown(insights: list[Insight]) -> dict[str, DrilldownPanelView]:
    output: dict[str, DrilldownPanelView] = {}
    for insight in insights:
        output[insight.insight_id] = DrilldownPanelView(
            item_id=insight.insight_id,
            item_type=f"insight:{insight.granularity}",
            title=insight.title,
            content=insight.content,
            evidence_segment_ids=insight.evidence_segment_ids,
        )
    return output


def _build_graph(
    document: StoryDocument,
    arcs: list[ArcSignal],
) -> tuple[list[GraphNode], list[GraphEdge]]:
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []

    for theme in document.theme_signals:
        nodes.append(
            GraphNode(
                id=theme.theme_id,
                label=theme.label,
                group="theme",
                stage=theme.stage,
            )
        )
    for beat in document.story_beats:
        nodes.append(
            GraphNode(
                id=beat.beat_id,
                label=f"B{beat.order_index}",
                group="beat",
                stage=beat.stage,
            )
        )
    for arc in arcs[:24]:
        node_id = f"arc_{arc.entity_id}_{arc.stage}"
        nodes.append(
            GraphNode(
                id=node_id,
                label=arc.entity_name,
                group="character",
                stage=arc.stage,
            )
        )

    theme_ids = [theme.theme_id for theme in document.theme_signals]
    beat_ids = [beat.beat_id for beat in document.story_beats]
    # TODO(#9): Replace dense theme->beat linking with evidence-driven graph edges.
    for theme_id in theme_ids:
        for beat_id in beat_ids:
            edges.append(
                GraphEdge(
                    source=theme_id,
                    target=beat_id,
                    relation="expressed_in",
                    weight=0.5,
                )
            )
    return _layout_graph_nodes(nodes), edges


def _layout_graph_nodes(nodes: list[GraphNode]) -> list[GraphNode]:
    stage_column: dict[StoryStage, int] = {
        "setup": 0,
        "escalation": 1,
        "climax": 2,
        "resolution": 3,
    }
    row_base = {
        "theme": 80,
        "beat": 220,
        "character": 360,
    }
    slot_counts: dict[tuple[str, int], int] = {}
    positioned: list[GraphNode] = []
    for node in nodes:
        column = stage_column[node.stage] if node.stage is not None else 4
        slot_key = (node.group, column)
        slot_index = slot_counts.get(slot_key, 0)
        slot_counts[slot_key] = slot_index + 1
        x = 110 + column * 180 + ((slot_index % 3) - 1) * 34
        y = row_base.get(node.group, 430) + (slot_index // 3) * 26
        positioned.append(
            GraphNode(
                id=node.id,
                label=node.label,
                group=node.group,
                stage=node.stage,
                layout_x=x,
                layout_y=y,
            )
        )
    return positioned
