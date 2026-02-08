from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from story_gen.adapters.sqlite_story_analysis_store import SQLiteStoryAnalysisStore
from story_gen.core.story_analysis_pipeline import StoryAnalysisResult, run_story_analysis


def _analysis_result(story_id: str) -> StoryAnalysisResult:
    return run_story_analysis(
        story_id=story_id,
        source_text=(
            "Rhea discovers the hidden records. "
            "The council rejects her claim. "
            "She proves the evidence in public."
        ),
    )


def test_story_analysis_store_write_and_read_latest(tmp_path: Path) -> None:
    db_path = tmp_path / "analysis.db"
    store = SQLiteStoryAnalysisStore(db_path=db_path)
    result = _analysis_result("story-a")
    run = store.write_analysis_result(owner_id="owner-1", result=result)
    latest = store.get_latest_analysis(owner_id="owner-1", story_id="story-a")
    assert latest is not None
    latest_run, document, dashboard, graph_svg = latest
    assert latest_run.run_id == run.run_id
    assert document.story_id == "story-a"
    assert dashboard["overview"]["events_count"] >= 1
    assert graph_svg.startswith("<svg")


def test_story_analysis_store_rejects_schema_mismatch(tmp_path: Path) -> None:
    db_path = tmp_path / "analysis.db"
    store = SQLiteStoryAnalysisStore(db_path=db_path)
    store.write_analysis_result(owner_id="owner-1", result=_analysis_result("story-b"))

    with sqlite3.connect(str(db_path)) as connection:
        connection.execute(
            """
            UPDATE analysis_schema_versions
            SET schema_version = 'story_analysis.v0'
            WHERE schema_key = 'story_analysis_runs'
            """
        )

    with pytest.raises(RuntimeError, match="schema version mismatch"):
        SQLiteStoryAnalysisStore(db_path=db_path)
