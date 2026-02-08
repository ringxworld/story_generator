"""CLI for running story feature extraction on a stored story record."""

from __future__ import annotations

import argparse
from pathlib import Path

from story_gen.adapters.sqlite_feature_store import SQLiteFeatureStore
from story_gen.adapters.sqlite_story_store import SQLiteStoryStore
from story_gen.api.contracts import StoryBlueprint
from story_gen.core.story_feature_pipeline import ChapterFeatureInput, extract_story_features


def build_arg_parser() -> argparse.ArgumentParser:
    """Define CLI flags for story feature extraction."""
    parser = argparse.ArgumentParser(description="Extract chapter-level features for one story.")
    parser.add_argument("--db-path", default="work/local/story_gen.db")
    parser.add_argument("--story-id", required=True)
    parser.add_argument("--owner-id", required=True)
    return parser


def main(argv: list[str] | None = None) -> None:
    """Run extraction for one story and persist a feature run."""
    parser = build_arg_parser()
    parsed = parser.parse_args(argv)

    db_path = Path(str(parsed.db_path))
    story_store = SQLiteStoryStore(db_path=db_path)
    feature_store = SQLiteFeatureStore(db_path=db_path)
    story = story_store.get_story(story_id=str(parsed.story_id))
    if story is None:
        raise SystemExit(f"Story not found: {parsed.story_id}")
    if story.owner_id != str(parsed.owner_id):
        raise SystemExit("Owner mismatch for requested story.")

    blueprint = StoryBlueprint.model_validate_json(story.blueprint_json)
    chapter_inputs = [
        ChapterFeatureInput(
            chapter_key=chapter.key,
            title=chapter.title,
            text=chapter.draft_text or chapter.objective,
        )
        for chapter in blueprint.chapters
    ]
    result = extract_story_features(story_id=story.story_id, chapters=chapter_inputs)
    run = feature_store.write_feature_result(owner_id=story.owner_id, result=result)

    print(f"Feature run id: {run.run_id}")
    print(f"Story id: {run.story_id}")
    print(f"Schema version: {run.schema_version}")
    print(f"Chapters extracted: {len(result.chapter_features)}")


if __name__ == "__main__":
    main()
