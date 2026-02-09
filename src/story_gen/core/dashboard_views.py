"""Dashboard read model projections from canonical story analysis artifacts."""

from __future__ import annotations

import binascii
import struct
import zlib
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
    drilldown = _build_drilldown(
        document.insights, document.theme_signals, arcs, conflicts, emotions
    )
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
    node_coords = _graph_node_positions(nodes=nodes, width=width, height=height)
    circles: list[str] = []
    labels: list[str] = []

    for node in nodes:
        x, y = node_coords[node.id]
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


def export_graph_png(*, nodes: list[GraphNode], edges: list[GraphEdge]) -> bytes:
    """Export graph projection to deterministic PNG bytes."""
    width = 900
    height = 520
    node_coords = _graph_node_positions(nodes=nodes, width=width, height=height)

    canvas = bytearray(width * height * 4)
    _fill_canvas(canvas=canvas, width=width, height=height, color=(0xEE, 0xF5, 0xF2, 0xFF))

    for edge in edges:
        source = node_coords.get(edge.source)
        target = node_coords.get(edge.target)
        if source is None or target is None:
            continue
        _draw_line(
            canvas=canvas,
            width=width,
            height=height,
            start=source,
            end=target,
            color=(0x5C, 0x8B, 0x7A, 0xFF),
            thickness=2,
        )

    for node in nodes:
        x, y = node_coords[node.id]
        _draw_filled_circle(
            canvas=canvas,
            width=width,
            height=height,
            center=(x, y),
            radius=16,
            color=(0x2E, 0x5E, 0x4E, 0xFF),
        )
        _draw_circle_stroke(
            canvas=canvas,
            width=width,
            height=height,
            center=(x, y),
            radius=16,
            stroke_width=2,
            color=(0x17, 0x36, 0x29, 0xFF),
        )

    return _encode_png(width=width, height=height, rgba=bytes(canvas))


def _graph_node_positions(
    *, nodes: list[GraphNode], width: int, height: int
) -> dict[str, tuple[int, int]]:
    del height
    x_step = max(100, width // max(len(nodes), 1))
    node_coords: dict[str, tuple[int, int]] = {}
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
    return node_coords


def _fill_canvas(
    *, canvas: bytearray, width: int, height: int, color: tuple[int, int, int, int]
) -> None:
    pixel = bytes(color)
    row = pixel * width
    for y in range(height):
        offset = y * width * 4
        canvas[offset : offset + width * 4] = row


def _draw_line(
    *,
    canvas: bytearray,
    width: int,
    height: int,
    start: tuple[int, int],
    end: tuple[int, int],
    color: tuple[int, int, int, int],
    thickness: int,
) -> None:
    x0, y0 = start
    x1, y1 = end
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    radius = max(0, thickness // 2)

    while True:
        for oy in range(-radius, radius + 1):
            for ox in range(-radius, radius + 1):
                _set_pixel(
                    canvas=canvas,
                    width=width,
                    height=height,
                    x=x0 + ox,
                    y=y0 + oy,
                    color=color,
                )
        if x0 == x1 and y0 == y1:
            break
        twice = err * 2
        if twice > -dy:
            err -= dy
            x0 += sx
        if twice < dx:
            err += dx
            y0 += sy


def _draw_filled_circle(
    *,
    canvas: bytearray,
    width: int,
    height: int,
    center: tuple[int, int],
    radius: int,
    color: tuple[int, int, int, int],
) -> None:
    cx, cy = center
    radius_sq = radius * radius
    for y in range(cy - radius, cy + radius + 1):
        for x in range(cx - radius, cx + radius + 1):
            dx = x - cx
            dy = y - cy
            if dx * dx + dy * dy <= radius_sq:
                _set_pixel(canvas=canvas, width=width, height=height, x=x, y=y, color=color)


def _draw_circle_stroke(
    *,
    canvas: bytearray,
    width: int,
    height: int,
    center: tuple[int, int],
    radius: int,
    stroke_width: int,
    color: tuple[int, int, int, int],
) -> None:
    cx, cy = center
    outer_sq = radius * radius
    inner_radius = max(0, radius - stroke_width)
    inner_sq = inner_radius * inner_radius
    for y in range(cy - radius, cy + radius + 1):
        for x in range(cx - radius, cx + radius + 1):
            dx = x - cx
            dy = y - cy
            distance_sq = dx * dx + dy * dy
            if inner_sq <= distance_sq <= outer_sq:
                _set_pixel(canvas=canvas, width=width, height=height, x=x, y=y, color=color)


def _set_pixel(
    *,
    canvas: bytearray,
    width: int,
    height: int,
    x: int,
    y: int,
    color: tuple[int, int, int, int],
) -> None:
    if not (0 <= x < width and 0 <= y < height):
        return
    offset = (y * width + x) * 4
    canvas[offset] = color[0]
    canvas[offset + 1] = color[1]
    canvas[offset + 2] = color[2]
    canvas[offset + 3] = color[3]


def _png_chunk(tag: bytes, payload: bytes) -> bytes:
    crc = binascii.crc32(tag + payload) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + tag + payload + struct.pack(">I", crc)


def _encode_png(*, width: int, height: int, rgba: bytes) -> bytes:
    row_bytes = width * 4
    expected = row_bytes * height
    if len(rgba) != expected:
        raise ValueError(f"RGBA byte size mismatch: got {len(rgba)}, expected {expected}")

    raw = bytearray()
    for row in range(height):
        raw.append(0)
        start = row * row_bytes
        raw.extend(rgba[start : start + row_bytes])

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    compressed = zlib.compress(bytes(raw), level=9)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", compressed)
        + _png_chunk(b"IEND", b"")
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


def _build_drilldown(
    insights: list[Insight],
    themes: list[ThemeSignal],
    arcs: list[ArcSignal],
    conflicts: list[ConflictShift],
    emotions: list[EmotionSignal],
) -> dict[str, DrilldownPanelView]:
    output: dict[str, DrilldownPanelView] = {}
    for insight in insights:
        output[insight.insight_id] = DrilldownPanelView(
            item_id=insight.insight_id,
            item_type=f"insight:{insight.granularity}",
            title=insight.title,
            content=insight.content,
            evidence_segment_ids=insight.evidence_segment_ids,
        )
    for theme in themes:
        item_id = f"theme:{theme.theme_id}"
        output[item_id] = DrilldownPanelView(
            item_id=item_id,
            item_type="theme",
            title=f"Theme: {theme.label} ({theme.stage})",
            content=(
                f"Strength {theme.strength:.2f}; trend {theme.direction}; "
                f"confidence {theme.confidence.score:.2f}."
            ),
            evidence_segment_ids=theme.evidence_segment_ids,
        )
    for arc in arcs:
        item_id = f"arc:{arc.entity_id}:{arc.stage}"
        output[item_id] = DrilldownPanelView(
            item_id=item_id,
            item_type="arc",
            title=f"Character Arc: {arc.entity_name} ({arc.stage})",
            content=f"State {arc.state}; delta {arc.delta:+.2f}; confidence {arc.confidence:.2f}.",
            evidence_segment_ids=list(arc.evidence_segment_ids),
        )
    for conflict in conflicts:
        item_id = f"conflict:{conflict.from_state}:{conflict.to_state}"
        output[item_id] = DrilldownPanelView(
            item_id=item_id,
            item_type="conflict",
            title=f"Conflict Shift: {conflict.from_state} -> {conflict.to_state}",
            content=(
                f"Intensity delta {conflict.intensity_delta:+.2f}; "
                f"confidence {conflict.confidence:.2f}."
            ),
            evidence_segment_ids=list(conflict.evidence_segment_ids),
        )
    for emotion in emotions:
        item_id = f"emotion:{emotion.stage}"
        output[item_id] = DrilldownPanelView(
            item_id=item_id,
            item_type="emotion",
            title=f"Emotion: {emotion.stage}",
            content=f"Tone {emotion.tone}; score {emotion.score:.2f}; confidence {emotion.confidence:.2f}.",
            evidence_segment_ids=list(emotion.evidence_segment_ids),
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
