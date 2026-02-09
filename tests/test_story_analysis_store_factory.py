from __future__ import annotations

from pathlib import Path

import pytest

from story_gen.adapters.graph_story_analysis_store import GraphStoryAnalysisStore
from story_gen.adapters.mongo_story_analysis_store import MongoStoryAnalysisStore
from story_gen.adapters.sqlite_story_analysis_store import SQLiteStoryAnalysisStore
from story_gen.adapters.story_analysis_store_factory import create_story_analysis_store
from story_gen.core.story_analysis_pipeline import run_story_analysis


def _sample_story() -> str:
    return (
        "Rhea enters the archive and finds her family's ledger. "
        "A conflict erupts when the council denies the records. "
        "She confronts the council in the central hall. "
        "The city accepts the truth and begins to heal."
    )


def test_factory_defaults_to_sqlite_backend(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("STORY_GEN_ANALYSIS_BACKEND", raising=False)
    monkeypatch.delenv("STORY_GEN_ENABLE_MONGO_ADAPTER", raising=False)
    monkeypatch.delenv("STORY_GEN_ENABLE_GRAPH_ADAPTER", raising=False)
    store = create_story_analysis_store(db_path=tmp_path / "story_gen.db")
    assert isinstance(store, SQLiteStoryAnalysisStore)


def test_factory_requires_feature_flag_for_mongo_backend(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("STORY_GEN_ANALYSIS_BACKEND", "mongo-prototype")
    monkeypatch.delenv("STORY_GEN_ENABLE_MONGO_ADAPTER", raising=False)
    with pytest.raises(RuntimeError, match="STORY_GEN_ENABLE_MONGO_ADAPTER"):
        create_story_analysis_store(db_path=tmp_path / "story_gen.db")


def test_factory_requires_feature_flag_for_graph_backend(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("STORY_GEN_ANALYSIS_BACKEND", "graph-prototype")
    monkeypatch.delenv("STORY_GEN_ENABLE_GRAPH_ADAPTER", raising=False)
    with pytest.raises(RuntimeError, match="STORY_GEN_ENABLE_GRAPH_ADAPTER"):
        create_story_analysis_store(db_path=tmp_path / "story_gen.db")


def test_factory_supports_mongo_and_graph_backends_when_enabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("STORY_GEN_ANALYSIS_BACKEND", "mongo-prototype")
    monkeypatch.setenv("STORY_GEN_ENABLE_MONGO_ADAPTER", "1")
    mongo_store = create_story_analysis_store(db_path=tmp_path / "story_gen.db")
    assert isinstance(mongo_store, MongoStoryAnalysisStore)

    monkeypatch.setenv("STORY_GEN_ANALYSIS_BACKEND", "graph-prototype")
    monkeypatch.setenv("STORY_GEN_ENABLE_GRAPH_ADAPTER", "1")
    graph_store = create_story_analysis_store(db_path=tmp_path / "story_gen.db")
    assert isinstance(graph_store, GraphStoryAnalysisStore)


@pytest.mark.parametrize("store_type", [MongoStoryAnalysisStore, GraphStoryAnalysisStore])
def test_prototype_backends_round_trip_latest_analysis(
    tmp_path: Path,
    store_type: type[MongoStoryAnalysisStore] | type[GraphStoryAnalysisStore],
) -> None:
    store = store_type(db_path=tmp_path / "story_gen.db")
    analysis = run_story_analysis(story_id="story-1", source_text=_sample_story())
    stored = store.write_analysis_result(owner_id="owner-1", result=analysis)
    loaded = store.get_latest_analysis(owner_id="owner-1", story_id="story-1")
    assert loaded is not None
    metadata, document, dashboard, graph_svg = loaded
    assert metadata.run_id == stored.run_id
    assert document.story_id == "story-1"
    assert "graph_nodes" in dashboard
    assert graph_svg.startswith("<svg")
