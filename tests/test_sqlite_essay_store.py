from __future__ import annotations

from pathlib import Path

from story_gen.adapters.sqlite_essay_store import SQLiteEssayStore
from story_gen.adapters.sqlite_story_store import SQLiteStoryStore


def _blueprint_json() -> str:
    return (
        '{"prompt":"Write clearly.","policy":{"thesis_statement":"x","audience":"y","tone":"z",'
        '"min_words":100,"max_words":300,"required_sections":[{"key":"introduction","purpose":"p",'
        '"min_paragraphs":1,"required_terms":[]}],"banned_phrases":[],"required_citations":0},'
        '"rubric":[]}'
    )


def test_essay_store_crud_lifecycle(tmp_path: Path) -> None:
    story_store = SQLiteStoryStore(db_path=tmp_path / "stories.db")
    user = story_store.create_user(
        email="alice@example.com", display_name="Alice", password_hash="hash"
    )
    assert user is not None
    essay_store = SQLiteEssayStore(db_path=tmp_path / "stories.db")

    created = essay_store.create_essay(
        owner_id=user.user_id,
        title="Essay One",
        blueprint_json=_blueprint_json(),
        draft_text="introduction: hello",
    )
    loaded = essay_store.get_essay(essay_id=created.essay_id)
    listed = essay_store.list_essays(owner_id=user.user_id)
    updated = essay_store.update_essay(
        essay_id=created.essay_id,
        title="Essay One Revised",
        blueprint_json=_blueprint_json(),
        draft_text="introduction: updated",
    )

    assert loaded is not None
    assert loaded.title == "Essay One"
    assert len(listed) == 1
    assert updated is not None
    assert updated.title == "Essay One Revised"
    assert essay_store.get_essay(essay_id="missing") is None
