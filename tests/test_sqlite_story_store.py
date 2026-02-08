from __future__ import annotations

from pathlib import Path

from story_gen.adapters.sqlite_story_store import SQLiteStoryStore


def test_store_create_list_and_get(tmp_path: Path) -> None:
    store = SQLiteStoryStore(db_path=tmp_path / "stories.db")

    created = store.create_story(owner_id="alice", title="Hello", body="First draft")
    listed = store.list_stories(owner_id="alice")
    loaded = store.get_story(story_id=created.story_id)

    assert len(listed) == 1
    assert listed[0].story_id == created.story_id
    assert loaded is not None
    assert loaded.title == "Hello"


def test_store_update_and_missing_paths(tmp_path: Path) -> None:
    store = SQLiteStoryStore(db_path=tmp_path / "stories.db")
    created = store.create_story(owner_id="alice", title="Before", body="Draft")

    updated = store.update_story(
        story_id=created.story_id,
        title="After",
        body="Revised draft",
    )
    missing = store.update_story(
        story_id="missing-story-id",
        title="Never",
        body="Applied nowhere",
    )

    assert updated is not None
    assert updated.title == "After"
    assert missing is None
    assert store.get_story(story_id="missing-story-id") is None
