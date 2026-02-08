from __future__ import annotations

import pytest

from story_gen.core.story_feature_pipeline import (
    FEATURE_SCHEMA_VERSION,
    ChapterFeatureInput,
    extract_story_features,
)


def test_extract_story_features_computes_rows() -> None:
    result = extract_story_features(
        story_id="story-1",
        chapters=[
            ChapterFeatureInput(
                chapter_key="ch01",
                title="Chapter 1",
                text='"Hello there."\nNarration line follows. Another sentence!',
            ),
            ChapterFeatureInput(
                chapter_key="ch02",
                title="Chapter 2",
                text="Action sequence starts now. Then slows down.",
            ),
        ],
    )
    assert result.schema_version == FEATURE_SCHEMA_VERSION
    assert len(result.chapter_features) == 2
    assert result.chapter_features[0].chapter_index == 1
    assert result.chapter_features[0].dialogue_line_ratio > 0
    assert result.chapter_features[1].sentence_count >= 1


def test_extract_story_features_rejects_empty_inputs() -> None:
    with pytest.raises(ValueError, match="At least one chapter"):
        extract_story_features(story_id="story-1", chapters=[])

    with pytest.raises(ValueError, match="must not be empty"):
        extract_story_features(
            story_id="",
            chapters=[ChapterFeatureInput(chapter_key="ch01", title="x", text="text")],
        )
