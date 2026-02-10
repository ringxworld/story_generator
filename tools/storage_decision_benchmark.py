"""Benchmark Mongo-style document access vs graph-index traversal patterns."""

from __future__ import annotations

import argparse
import json
import random
import statistics
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter_ns
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "work" / "benchmarks" / "storage_decision_spike.v1.json"
STAGES = ("setup", "escalation", "climax", "resolution")


@dataclass(frozen=True)
class StoryGraph:
    owner_id: str
    story_id: str
    nodes: list[dict[str, str]]
    edges: list[dict[str, str]]
    themes: list[str]
    characters: list[str]


class DocumentQueryModel:
    """Mongo-style model where graph traversal scans embedded edge arrays."""

    def __init__(self, stories: list[StoryGraph]) -> None:
        self._documents: dict[tuple[str, str], StoryGraph] = {
            (story.owner_id, story.story_id): story for story in stories
        }
        self.keys = list(self._documents)

    def latest_story_lookup(self, key: tuple[str, str]) -> StoryGraph:
        return self._documents[key]

    def related_beats_for_theme(self, key: tuple[str, str], theme_id: str) -> set[str]:
        story = self._documents[key]
        beats: set[str] = set()
        for edge in story.edges:
            if edge["source"] == theme_id and edge["target"].startswith("beat_"):
                beats.add(edge["target"])
            elif edge["target"] == theme_id and edge["source"].startswith("beat_"):
                beats.add(edge["source"])
        return beats

    def two_hop_context(self, key: tuple[str, str], node_id: str) -> set[str]:
        story = self._documents[key]
        first_hop: set[str] = set()
        for edge in story.edges:
            if edge["source"] == node_id:
                first_hop.add(edge["target"])
            elif edge["target"] == node_id:
                first_hop.add(edge["source"])
        second_hop: set[str] = set()
        for edge in story.edges:
            if edge["source"] in first_hop:
                second_hop.add(edge["target"])
            if edge["target"] in first_hop:
                second_hop.add(edge["source"])
        second_hop.discard(node_id)
        return second_hop


class GraphQueryModel:
    """Graph model with precomputed adjacency and relation indexes."""

    def __init__(self, stories: list[StoryGraph]) -> None:
        self.keys: list[tuple[str, str]] = []
        self._graph_index: dict[
            tuple[str, str], dict[str, dict[str, set[str]] | dict[tuple[str, str], set[str]]]
        ] = {}
        for story in stories:
            key = (story.owner_id, story.story_id)
            self.keys.append(key)
            adjacency: dict[str, set[str]] = {}
            relation_index: dict[tuple[str, str], set[str]] = {}
            for edge in story.edges:
                source = edge["source"]
                target = edge["target"]
                relation = edge["relation"]
                adjacency.setdefault(source, set()).add(target)
                adjacency.setdefault(target, set()).add(source)
                relation_index.setdefault((source, relation), set()).add(target)
                relation_index.setdefault((target, relation), set()).add(source)
            self._graph_index[key] = {
                "adjacency": adjacency,
                "relation_index": relation_index,
            }

    def latest_story_lookup(self, key: tuple[str, str]) -> dict[str, Any]:
        return self._graph_index[key]

    def related_beats_for_theme(self, key: tuple[str, str], theme_id: str) -> set[str]:
        relation_index = self._graph_index[key]["relation_index"]
        assert isinstance(relation_index, dict)
        related = set()
        for relation in ("evidence_aligned", "stage_aligned", "expressed_in", "resolved_in"):
            related.update(
                node
                for node in relation_index.get((theme_id, relation), set())
                if node.startswith("beat_")
            )
        return related

    def two_hop_context(self, key: tuple[str, str], node_id: str) -> set[str]:
        adjacency = self._graph_index[key]["adjacency"]
        assert isinstance(adjacency, dict)
        first_hop = adjacency.get(node_id, set())
        second_hop: set[str] = set()
        for candidate in first_hop:
            second_hop.update(adjacency.get(candidate, set()))
        second_hop.discard(node_id)
        return second_hop


def _summary(latencies_us: list[float]) -> dict[str, float]:
    ordered = sorted(latencies_us)

    def percentile(p: float) -> float:
        if not ordered:
            return 0.0
        index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * p))))
        return round(ordered[index], 3)

    return {
        "p50_us": percentile(0.5),
        "p95_us": percentile(0.95),
        "mean_us": round(statistics.fmean(ordered), 3) if ordered else 0.0,
        "max_us": round(max(ordered), 3) if ordered else 0.0,
    }


def _measure(operation: callable, cases: list[tuple[Any, ...]]) -> dict[str, float]:
    latencies_us: list[float] = []
    for case in cases:
        started = perf_counter_ns()
        operation(*case)
        elapsed_ns = perf_counter_ns() - started
        latencies_us.append(elapsed_ns / 1_000.0)
    return _summary(latencies_us)


def _build_story_graph(*, rng: random.Random, owner_id: str, story_index: int) -> StoryGraph:
    story_id = f"story-{story_index:04d}"
    themes = [f"theme_{story_index}_{idx}" for idx in range(1, 9)]
    beats = [f"beat_{story_index}_{idx}" for idx in range(1, 13)]
    characters = [f"arc_char_{story_index}_{idx}" for idx in range(1, 7)]
    nodes: list[dict[str, str]] = []
    for theme_id in themes:
        nodes.append({"id": theme_id, "group": "theme", "stage": rng.choice(STAGES)})
    for beat_id in beats:
        nodes.append({"id": beat_id, "group": "beat", "stage": rng.choice(STAGES)})
    for character_id in characters:
        nodes.append({"id": character_id, "group": "character", "stage": rng.choice(STAGES)})

    relations = ("evidence_aligned", "stage_aligned", "drives", "about", "tracks")
    edges: list[dict[str, str]] = []
    for theme_id in themes:
        for beat_id in rng.sample(beats, k=4):
            edges.append(
                {
                    "source": theme_id,
                    "target": beat_id,
                    "relation": rng.choice(relations[:2]),
                }
            )
    for character_id in characters:
        for beat_id in rng.sample(beats, k=3):
            edges.append(
                {"source": character_id, "target": beat_id, "relation": rng.choice(relations)}
            )
    for _ in range(30):
        source = rng.choice(themes + characters)
        target = rng.choice(themes + beats + characters)
        if source == target:
            continue
        edges.append({"source": source, "target": target, "relation": rng.choice(relations)})
    return StoryGraph(
        owner_id=owner_id,
        story_id=story_id,
        nodes=nodes,
        edges=edges,
        themes=themes,
        characters=characters,
    )


def run_benchmark(*, stories: int, operations: int, seed: int) -> dict[str, object]:
    rng = random.Random(seed)
    corpus = [
        _build_story_graph(rng=rng, owner_id=f"owner-{index % 12}", story_index=index)
        for index in range(stories)
    ]
    document_model = DocumentQueryModel(corpus)
    graph_model = GraphQueryModel(corpus)
    story_by_key = {(story.owner_id, story.story_id): story for story in corpus}
    key_cases = [rng.choice(document_model.keys) for _ in range(operations)]
    theme_cases = [
        (key, rng.choice(story_by_key[key].themes))
        for key in [rng.choice(document_model.keys) for _ in range(operations)]
    ]
    two_hop_cases = [
        (key, rng.choice(story_by_key[key].characters))
        for key in [rng.choice(document_model.keys) for _ in range(operations)]
    ]
    results = {
        "latest_story_lookup": {
            "mongo_style_document": _measure(
                document_model.latest_story_lookup, [(case,) for case in key_cases]
            ),
            "graph_indexed": _measure(
                graph_model.latest_story_lookup, [(case,) for case in key_cases]
            ),
        },
        "related_beats_for_theme": {
            "mongo_style_document": _measure(document_model.related_beats_for_theme, theme_cases),
            "graph_indexed": _measure(graph_model.related_beats_for_theme, theme_cases),
        },
        "two_hop_context": {
            "mongo_style_document": _measure(document_model.two_hop_context, two_hop_cases),
            "graph_indexed": _measure(graph_model.two_hop_context, two_hop_cases),
        },
    }
    return {
        "benchmark_version": "storage_decision_spike.v1",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "config": {"stories": stories, "operations_per_query": operations, "seed": seed},
        "results": results,
    }


def _print_summary(payload: dict[str, object]) -> None:
    results = payload["results"]
    assert isinstance(results, dict)
    print("Query | Model | p50 us | p95 us | mean us | max us")
    for query, models in results.items():
        assert isinstance(models, dict)
        for model, metrics in models.items():
            assert isinstance(metrics, dict)
            print(
                f"{query} | {model} | {metrics['p50_us']} | {metrics['p95_us']} | "
                f"{metrics['mean_us']} | {metrics['max_us']}"
            )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Benchmark storage query patterns for document vs graph model decisions."
    )
    parser.add_argument("--stories", type=int, default=600)
    parser.add_argument("--operations", type=int, default=2_500)
    parser.add_argument("--seed", type=int, default=104729)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    payload = run_benchmark(stories=args.stories, operations=args.operations, seed=args.seed)
    output_path = Path(str(args.output)).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    _print_summary(payload)
    print(f"Wrote benchmark report: {output_path}")


if __name__ == "__main__":
    main()
