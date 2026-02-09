"""CLI for deterministic dashboard graph exports."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import cast

from pydantic import ValidationError

from story_gen.adapters.sqlite_story_analysis_store import SQLiteStoryAnalysisStore
from story_gen.adapters.sqlite_story_store import SQLiteStoryStore
from story_gen.api.contracts import DashboardGraphEdgeResponse, DashboardGraphNodeResponse
from story_gen.core.dashboard_views import GraphEdge, GraphNode, export_graph_png
from story_gen.core.story_schema import StoryStage


def build_arg_parser() -> argparse.ArgumentParser:
    """Define CLI flags for dashboard graph export."""
    parser = argparse.ArgumentParser(description="Export dashboard graph as SVG or PNG.")
    parser.add_argument("--db-path", default="work/local/story_gen.db")
    parser.add_argument("--story-id", required=True)
    parser.add_argument("--owner-id", required=True)
    parser.add_argument("--format", choices=["svg", "png"], default="svg")
    parser.add_argument("--output", required=True, help="Output file path.")
    return parser


def _graph_projection(
    *, dashboard: dict[str, object], story_id: str
) -> tuple[list[GraphNode], list[GraphEdge]]:
    raw_nodes = dashboard.get("graph_nodes")
    raw_edges = dashboard.get("graph_edges")
    if not isinstance(raw_nodes, list):
        raise SystemExit(f"Dashboard payload missing graph_nodes array for story {story_id}.")
    if not isinstance(raw_edges, list):
        raise SystemExit(f"Dashboard payload missing graph_edges array for story {story_id}.")
    try:
        nodes = [DashboardGraphNodeResponse.model_validate(item) for item in raw_nodes]
        edges = [DashboardGraphEdgeResponse.model_validate(item) for item in raw_edges]
    except ValidationError as exc:
        raise SystemExit(f"Dashboard graph payload is invalid for story {story_id}: {exc}") from exc
    return (
        [
            GraphNode(
                id=node.id,
                label=node.label,
                group=node.group,
                stage=cast(StoryStage | None, node.stage),
                layout_x=node.layout_x,
                layout_y=node.layout_y,
            )
            for node in nodes
        ],
        [
            GraphEdge(
                source=edge.source,
                target=edge.target,
                relation=edge.relation,
                weight=edge.weight,
            )
            for edge in edges
        ],
    )


def main(argv: list[str] | None = None) -> None:
    """Export one owner-scoped story dashboard graph snapshot."""
    parser = build_arg_parser()
    parsed = parser.parse_args(argv)

    db_path = Path(str(parsed.db_path))
    story_id = str(parsed.story_id)
    owner_id = str(parsed.owner_id)
    output_path = Path(str(parsed.output))
    export_format = str(parsed.format)

    story_store = SQLiteStoryStore(db_path=db_path)
    analysis_store = SQLiteStoryAnalysisStore(db_path=db_path)
    story = story_store.get_story(story_id=story_id)
    if story is None:
        raise SystemExit(f"Story not found: {story_id}")
    if story.owner_id != owner_id:
        raise SystemExit(f"Owner mismatch for story {story_id}.")

    latest = analysis_store.get_latest_analysis(owner_id=owner_id, story_id=story_id)
    if latest is None:
        raise SystemExit(f"No analysis run found for story {story_id}.")
    _, _, dashboard, graph_svg = latest

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if export_format == "svg":
        output_path.write_text(graph_svg, encoding="utf-8")
    else:
        nodes, edges = _graph_projection(dashboard=dashboard, story_id=story_id)
        output_path.write_bytes(export_graph_png(nodes=nodes, edges=edges))

    print(f"Wrote {export_format.upper()} export: {output_path}")
    print(f"Story id: {story_id}")
    print(f"Owner id: {owner_id}")


if __name__ == "__main__":
    main()
