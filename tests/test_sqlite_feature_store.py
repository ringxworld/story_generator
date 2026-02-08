from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from story_gen.adapters.sqlite_feature_store import SQLiteFeatureStore
from story_gen.core.story_feature_pipeline import (
    ChapterFeatureInput,
    StoryFeatureExtractionResult,
    extract_story_features,
)


def _result_for_story(story_id: str) -> StoryFeatureExtractionResult:
    return extract_story_features(
        story_id=story_id,
        chapters=[
            ChapterFeatureInput(
                chapter_key="ch01",
                title="Chapter 1",
                text='"Hello."\nWorld building follows.',
            )
        ],
    )


def test_feature_store_write_and_read_latest(tmp_path: Path) -> None:
    db_path = tmp_path / "feature.db"
    store = SQLiteFeatureStore(db_path=db_path)
    run = store.write_feature_result(owner_id="owner-1", result=_result_for_story("story-1"))
    latest = store.get_latest_feature_result(owner_id="owner-1", story_id="story-1")
    assert latest is not None
    latest_run, latest_result = latest
    assert latest_run.run_id == run.run_id
    assert latest_result.story_id == "story-1"
    assert latest_result.chapter_features[0].chapter_key == "ch01"


def test_feature_store_rejects_schema_mismatch(tmp_path: Path) -> None:
    db_path = tmp_path / "feature.db"
    store = SQLiteFeatureStore(db_path=db_path)
    store.write_feature_result(owner_id="owner-1", result=_result_for_story("story-1"))

    with sqlite3.connect(str(db_path)) as connection:
        connection.execute(
            """
            UPDATE feature_schema_versions
            SET schema_version = 'story_features.v0'
            WHERE schema_key = 'story_feature_rows'
            """
        )

    with pytest.raises(RuntimeError, match="schema version mismatch"):
        SQLiteFeatureStore(db_path=db_path)
