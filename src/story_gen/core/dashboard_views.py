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

    legend = [
        '<rect x="24" y="18" width="250" height="44" rx="8" fill="#DCE8E3" />',
        '<circle cx="42" cy="40" r="8" fill="#2E5E4E" stroke="#173629" stroke-width="2" />',
        '<text x="56" y="44" fill="#10231C" font-size="11">theme / beat / character</text>',
        '<line x1="178" y1="40" x2="210" y2="40" stroke="#5C8B7A" stroke-width="2" />',
        '<text x="218" y="44" fill="#10231C" font-size="11">relation</text>',
    ]
    body = "\n".join(legend + lines + circles + labels)
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
    _draw_rect(
        canvas=canvas,
        width=width,
        height=height,
        x=24,
        y=18,
        rect_width=250,
        rect_height=44,
        color=(0xDC, 0xE8, 0xE3, 0xFF),
    )
    _draw_line(
        canvas=canvas,
        width=width,
        height=height,
        start=(178, 40),
        end=(210, 40),
        color=(0x5C, 0x8B, 0x7A, 0xFF),
        thickness=2,
    )
    _draw_filled_circle(
        canvas=canvas,
        width=width,
        height=height,
        center=(42, 40),
        radius=8,
        color=(0x2E, 0x5E, 0x4E, 0xFF),
    )
    _draw_circle_stroke(
        canvas=canvas,
        width=width,
        height=height,
        center=(42, 40),
        radius=8,
        stroke_width=2,
        color=(0x17, 0x36, 0x29, 0xFF),
    )

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


def export_timeline_svg(*, lanes: list[TimelineLaneView]) -> str:
    """Export timeline lanes to deterministic SVG text."""
    width = 960
    lane_count = max(len(lanes), 1)
    height = 180 + lane_count * 140
    stage_width = width - 220
    lane_rows: list[str] = []
    lane_labels: list[str] = []
    markers: list[str] = []
    item_labels: list[str] = []

    lane_spacing = max(
        1, stage_width // max(1, max((len(lane.items) for lane in lanes), default=1))
    )
    for lane_index, lane in enumerate(lanes):
        y = 120 + lane_index * 140
        lane_labels.append(
            f'<text x="38" y="{y + 6}" fill="#163229" font-size="15">{escape(lane.lane)}</text>'
        )
        lane_rows.append(
            f'<line x1="210" y1="{y}" x2="{width - 40}" y2="{y}" stroke="#8BA49B" stroke-width="2" />'
        )
        for item_index, item in enumerate(lane.items):
            x = min(width - 40, 210 + lane_spacing // 2 + item_index * lane_spacing)
            label_raw = str(item.get("label", "event"))
            label = label_raw if len(label_raw) <= 22 else f"{label_raw[:19]}..."
            has_time = item.get("time") is not None
            fill = "#2E5E4E" if has_time else "#4A6E9B"
            markers.append(
                f'<circle cx="{x}" cy="{y}" r="9" fill="{fill}" stroke="#173629" stroke-width="2" />'
            )
            item_labels.append(
                f'<text x="{x}" y="{y + 30}" text-anchor="middle" fill="#163229" font-size="12">{escape(label)}</text>'
            )

    legend = [
        '<rect x="38" y="28" width="18" height="18" fill="#2E5E4E" />',
        '<text x="64" y="42" fill="#163229" font-size="12">timestamp present</text>',
        '<rect x="220" y="28" width="18" height="18" fill="#4A6E9B" />',
        '<text x="246" y="42" fill="#163229" font-size="12">timestamp missing</text>',
    ]
    if not lanes:
        item_labels.append(
            '<text x="40" y="120" fill="#163229" font-size="14">No timeline lanes available.</text>'
        )
    body = "\n".join(legend + lane_rows + lane_labels + markers + item_labels)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}"><rect width="100%" height="100%" fill="#EEF5F2" />'
        f'<text x="38" y="84" fill="#10231C" font-size="24">Timeline Export</text>{body}</svg>'
    )


def export_timeline_png(*, lanes: list[TimelineLaneView]) -> bytes:
    """Export timeline lanes to deterministic PNG bytes."""
    width = 960
    lane_count = max(len(lanes), 1)
    height = 180 + lane_count * 140
    canvas = bytearray(width * height * 4)
    _fill_canvas(canvas=canvas, width=width, height=height, color=(0xEE, 0xF5, 0xF2, 0xFF))
    _draw_rect(
        canvas=canvas,
        width=width,
        height=height,
        x=32,
        y=26,
        rect_width=20,
        rect_height=20,
        color=(0x2E, 0x5E, 0x4E, 0xFF),
    )
    _draw_rect(
        canvas=canvas,
        width=width,
        height=height,
        x=216,
        y=26,
        rect_width=20,
        rect_height=20,
        color=(0x4A, 0x6E, 0x9B, 0xFF),
    )
    if lanes:
        stage_width = width - 220
        lane_spacing = max(
            1, stage_width // max(1, max((len(lane.items) for lane in lanes), default=1))
        )
        for lane_index, lane in enumerate(lanes):
            y = 120 + lane_index * 140
            _draw_line(
                canvas=canvas,
                width=width,
                height=height,
                start=(210, y),
                end=(width - 40, y),
                color=(0x8B, 0xA4, 0x9B, 0xFF),
                thickness=2,
            )
            for item_index, item in enumerate(lane.items):
                x = min(width - 40, 210 + lane_spacing // 2 + item_index * lane_spacing)
                fill = (
                    (0x2E, 0x5E, 0x4E, 0xFF)
                    if item.get("time") is not None
                    else (0x4A, 0x6E, 0x9B, 0xFF)
                )
                _draw_filled_circle(
                    canvas=canvas,
                    width=width,
                    height=height,
                    center=(x, y),
                    radius=9,
                    color=fill,
                )
                _draw_circle_stroke(
                    canvas=canvas,
                    width=width,
                    height=height,
                    center=(x, y),
                    radius=9,
                    stroke_width=2,
                    color=(0x17, 0x36, 0x29, 0xFF),
                )
    return _encode_png(width=width, height=height, rgba=bytes(canvas))


def export_theme_heatmap_svg(*, cells: list[ThemeHeatmapCell]) -> str:
    """Export theme heatmap cells to deterministic SVG text."""
    ordered_cells = sorted(cells, key=lambda cell: (cell.theme, cell.stage))
    themes = sorted({cell.theme for cell in ordered_cells})
    stages: list[StoryStage] = ["setup", "escalation", "climax", "resolution"]

    width = 980
    height = 220 + max(len(themes), 1) * 56
    cell_width = 150
    cell_height = 42
    grid_start_x = 280
    grid_start_y = 110
    values: dict[tuple[str, StoryStage], float] = {
        (cell.theme, cell.stage): cell.intensity for cell in ordered_cells
    }

    headers = [
        f'<text x="{grid_start_x + index * cell_width + 10}" y="92" fill="#163229" font-size="13">{stage}</text>'
        for index, stage in enumerate(stages)
    ]
    rows: list[str] = []
    labels: list[str] = []
    for row_index, theme in enumerate(themes):
        y = grid_start_y + row_index * cell_height
        labels.append(
            f'<text x="34" y="{y + 26}" fill="#163229" font-size="14">{escape(theme)}</text>'
        )
        for col_index, stage in enumerate(stages):
            x = grid_start_x + col_index * cell_width
            intensity = max(0.0, min(1.0, values.get((theme, stage), 0.0)))
            fill = _rgb_hex(_heatmap_color(intensity))
            rows.append(
                f'<rect x="{x}" y="{y}" width="{cell_width - 8}" height="{cell_height - 8}" fill="{fill}" stroke="#D9E7E1" stroke-width="1" />'
            )

    legend = [
        '<text x="34" y="48" fill="#163229" font-size="12">Low</text>',
        '<rect x="72" y="34" width="26" height="14" fill="#EEF5F2" stroke="#D9E7E1" />',
        '<rect x="100" y="34" width="26" height="14" fill="#CBE2D8" stroke="#D9E7E1" />',
        '<rect x="128" y="34" width="26" height="14" fill="#A4CFC0" stroke="#D9E7E1" />',
        '<rect x="156" y="34" width="26" height="14" fill="#7AB9A5" stroke="#D9E7E1" />',
        '<rect x="184" y="34" width="26" height="14" fill="#2E5E4E" stroke="#D9E7E1" />',
        '<text x="218" y="48" fill="#163229" font-size="12">High</text>',
    ]
    if not themes:
        labels.append(
            '<text x="34" y="132" fill="#163229" font-size="14">No heatmap cells available.</text>'
        )
    body = "\n".join(legend + headers + labels + rows)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}"><rect width="100%" height="100%" fill="#F4F9F7" />'
        f'<text x="34" y="84" fill="#10231C" font-size="24">Theme Heatmap Export</text>{body}</svg>'
    )


def export_theme_heatmap_png(*, cells: list[ThemeHeatmapCell]) -> bytes:
    """Export theme heatmap cells to deterministic PNG bytes."""
    ordered_cells = sorted(cells, key=lambda cell: (cell.theme, cell.stage))
    themes = sorted({cell.theme for cell in ordered_cells})
    stages: list[StoryStage] = ["setup", "escalation", "climax", "resolution"]
    width = 980
    height = 220 + max(len(themes), 1) * 56
    cell_width = 150
    cell_height = 42
    grid_start_x = 280
    grid_start_y = 110
    values: dict[tuple[str, StoryStage], float] = {
        (cell.theme, cell.stage): cell.intensity for cell in ordered_cells
    }

    canvas = bytearray(width * height * 4)
    _fill_canvas(canvas=canvas, width=width, height=height, color=(0xF4, 0xF9, 0xF7, 0xFF))
    for index, color in enumerate(
        [
            (0xEE, 0xF5, 0xF2, 0xFF),
            (0xCB, 0xE2, 0xD8, 0xFF),
            (0xA4, 0xCF, 0xC0, 0xFF),
            (0x7A, 0xB9, 0xA5, 0xFF),
            (0x2E, 0x5E, 0x4E, 0xFF),
        ]
    ):
        _draw_rect(
            canvas=canvas,
            width=width,
            height=height,
            x=72 + index * 28,
            y=34,
            rect_width=26,
            rect_height=14,
            color=color,
        )

    for row_index, theme in enumerate(themes):
        y = grid_start_y + row_index * cell_height
        for col_index, stage in enumerate(stages):
            x = grid_start_x + col_index * cell_width
            intensity = max(0.0, min(1.0, values.get((theme, stage), 0.0)))
            _draw_rect(
                canvas=canvas,
                width=width,
                height=height,
                x=x,
                y=y,
                rect_width=cell_width - 8,
                rect_height=cell_height - 8,
                color=_heatmap_color(intensity),
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


def _draw_rect(
    *,
    canvas: bytearray,
    width: int,
    height: int,
    x: int,
    y: int,
    rect_width: int,
    rect_height: int,
    color: tuple[int, int, int, int],
) -> None:
    for row in range(y, y + rect_height):
        if not (0 <= row < height):
            continue
        start_x = max(0, x)
        end_x = min(width, x + rect_width)
        if start_x >= end_x:
            continue
        offset = (row * width + start_x) * 4
        pixel_count = end_x - start_x
        canvas[offset : offset + pixel_count * 4] = bytes(color) * pixel_count


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


def _heatmap_color(intensity: float) -> tuple[int, int, int, int]:
    bounded = max(0.0, min(1.0, intensity))
    low = (0xEE, 0xF5, 0xF2)
    high = (0x2E, 0x5E, 0x4E)
    return (
        _interpolate_channel(low[0], high[0], bounded),
        _interpolate_channel(low[1], high[1], bounded),
        _interpolate_channel(low[2], high[2], bounded),
        0xFF,
    )


def _interpolate_channel(start: int, end: int, ratio: float) -> int:
    return int(round(start + (end - start) * ratio))


def _rgb_hex(color: tuple[int, int, int, int]) -> str:
    return f"#{color[0]:02X}{color[1]:02X}{color[2]:02X}"


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

    beats_by_id = {beat.beat_id: beat for beat in document.story_beats}
    for theme in document.theme_signals:
        theme_evidence = set(theme.evidence_segment_ids)
        for beat in document.story_beats:
            beat_evidence = set(beat.evidence_segment_ids)
            overlap = len(theme_evidence.intersection(beat_evidence))
            stage_match = theme.stage == beat.stage
            if overlap == 0 and not stage_match:
                continue
            relation = "evidence_aligned" if overlap > 0 else "stage_aligned"
            weight = round(0.4 + min(0.45, overlap * 0.16) + (0.1 if stage_match else 0.0), 3)
            edges.append(
                GraphEdge(
                    source=theme.theme_id,
                    target=beat.beat_id,
                    relation=relation,
                    weight=min(1.0, weight),
                )
            )
    for arc in arcs[:24]:
        arc_node_id = f"arc_{arc.entity_id}_{arc.stage}"
        best_beat_id = next(
            (
                beat.beat_id
                for beat in document.story_beats
                if beat.stage == arc.stage
                and set(arc.evidence_segment_ids).intersection(beat.evidence_segment_ids)
            ),
            next((beat.beat_id for beat in document.story_beats if beat.stage == arc.stage), None),
        )
        if best_beat_id is None or best_beat_id not in beats_by_id:
            continue
        edges.append(
            GraphEdge(
                source=arc_node_id,
                target=best_beat_id,
                relation="drives",
                weight=round(min(1.0, max(0.35, arc.confidence)), 3),
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
