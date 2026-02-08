from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from story_gen.adapters.sqlite_story_store import SQLiteStoryStore


def test_user_and_story_lifecycle(tmp_path: Path) -> None:
    store = SQLiteStoryStore(db_path=tmp_path / "stories.db")
    user = store.create_user(email="alice@example.com", display_name="Alice", password_hash="hash")
    assert user is not None

    created = store.create_story(
        owner_id=user.user_id,
        title="Hello",
        blueprint_json='{"premise":"A","themes":[],"characters":[],"chapters":[],"canon_rules":[]}',
    )
    listed = store.list_stories(owner_id=user.user_id)
    loaded = store.get_story(story_id=created.story_id)

    assert len(listed) == 1
    assert listed[0].story_id == created.story_id
    assert loaded is not None
    assert loaded.title == "Hello"
    assert loaded.owner_id == user.user_id


def test_duplicate_user_and_missing_story_paths(tmp_path: Path) -> None:
    store = SQLiteStoryStore(db_path=tmp_path / "stories.db")
    created_user = store.create_user(
        email="alice@example.com", display_name="Alice", password_hash="hash"
    )
    assert created_user is not None
    duplicate_user = store.create_user(
        email="alice@example.com",
        display_name="Alice 2",
        password_hash="hash2",
    )
    assert duplicate_user is None
    created = store.create_story(
        owner_id=created_user.user_id,
        title="Before",
        blueprint_json='{"premise":"A","themes":[],"characters":[],"chapters":[],"canon_rules":[]}',
    )

    updated = store.update_story(
        story_id=created.story_id,
        title="After",
        blueprint_json='{"premise":"B","themes":[],"characters":[],"chapters":[],"canon_rules":[]}',
    )
    missing = store.update_story(
        story_id="missing-story-id",
        title="Never",
        blueprint_json='{"premise":"C","themes":[],"characters":[],"chapters":[],"canon_rules":[]}',
    )

    assert updated is not None
    assert updated.title == "After"
    assert missing is None
    assert store.get_story(story_id="missing-story-id") is None


def test_token_lookup_respects_expiration(tmp_path: Path) -> None:
    store = SQLiteStoryStore(db_path=tmp_path / "stories.db")
    user = store.create_user(email="alice@example.com", display_name="Alice", password_hash="hash")
    assert user is not None
    valid_expires = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    expired_expires = (datetime.now(UTC) - timedelta(hours=1)).isoformat()

    store.create_token(
        user_id=user.user_id, token_value="token-valid", expires_at_utc=valid_expires
    )
    store.create_token(
        user_id=user.user_id, token_value="token-expired", expires_at_utc=expired_expires
    )

    now = datetime.now(UTC).isoformat()
    valid_user = store.get_user_by_token(token_value="token-valid", now_utc=now)
    expired_user = store.get_user_by_token(token_value="token-expired", now_utc=now)

    assert valid_user is not None
    assert valid_user.user_id == user.user_id
    assert expired_user is None
