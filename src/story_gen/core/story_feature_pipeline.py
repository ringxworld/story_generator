"""Story-to-features extraction pipeline with strict typed outputs."""

from __future__ import annotations

import re
from collections import Counter
from datetime import UTC, datetime
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

FEATURE_SCHEMA_VERSION: Final[Literal["story_features.v1"]] = "story_features.v1"
STOPWORDS = {
    "the",
    "and",
    "that",
    "with",
    "this",
    "from",
    "have",
    "into",
    "there",
    "their",
    "your",
    "you",
    "for",
    "are",
    "was",
    "were",
    "not",
}


class FeatureModel(BaseModel):
    """Base model with strict schema settings for pipeline artifacts."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ChapterFeatureInput(FeatureModel):
    """Input chapter payload for feature extraction."""

    chapter_key: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=300)
    text: str = Field(min_length=1)

    @field_validator("chapter_key")
    @classmethod
    def _normalize_key(cls, value: str) -> str:
        return value.strip().lower()


class ChapterFeatureRow(FeatureModel):
    """One extracted feature row for a chapter text unit."""

    schema_version: Literal["story_features.v1"] = "story_features.v1"
    story_id: str = Field(min_length=1)
    chapter_key: str = Field(min_length=1, max_length=120)
    chapter_index: int = Field(ge=1)
    source_length_chars: int = Field(ge=1)
    sentence_count: int = Field(ge=1)
    token_count: int = Field(ge=1)
    avg_sentence_length: float = Field(ge=0.0)
    dialogue_line_ratio: float = Field(ge=0.0, le=1.0)
    top_keywords: list[str] = Field(default_factory=list)


class StoryFeatureExtractionResult(FeatureModel):
    """Run-level feature extraction artifact."""

    schema_version: Literal["story_features.v1"] = "story_features.v1"
    story_id: str = Field(min_length=1)
    extracted_at_utc: str
    chapter_features: list[ChapterFeatureRow]

    @field_validator("chapter_features")
    @classmethod
    def _require_rows(cls, value: list[ChapterFeatureRow]) -> list[ChapterFeatureRow]:
        if not value:
            raise ValueError("chapter_features must not be empty.")
        return value


def _tokenize(text: str) -> list[str]:
    latin_tokens = re.findall(r"[A-Za-z0-9_']+", text.lower())
    if latin_tokens:
        return latin_tokens
    return [token for token in re.split(r"\s+", text) if token.strip()]


def _sentence_split(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n")
    sentences = [
        chunk.strip() for chunk in re.split(r"[.!?。！？]+\s*", normalized) if chunk.strip()
    ]
    return sentences


def _dialogue_line_ratio(text: str) -> float:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return 0.0
    markers = ('"', "'", "“", "「", "『")
    dialogue_lines = sum(1 for line in lines if line.startswith(markers))
    return dialogue_lines / len(lines)


def _top_keywords(tokens: list[str], *, max_keywords: int = 8) -> list[str]:
    filtered = [token for token in tokens if len(token) >= 4 and token not in STOPWORDS]
    counts = Counter(filtered)
    return [token for token, _ in counts.most_common(max_keywords)]


def extract_story_features(
    *,
    story_id: str,
    chapters: list[ChapterFeatureInput],
) -> StoryFeatureExtractionResult:
    """Extract deterministic chapter-level features from story text."""
    if not chapters:
        raise ValueError("At least one chapter is required for feature extraction.")
    normalized_story_id = story_id.strip()
    if not normalized_story_id:
        raise ValueError("story_id must not be empty.")

    rows: list[ChapterFeatureRow] = []
    for index, chapter in enumerate(chapters, start=1):
        text = chapter.text.strip()
        if not text:
            raise ValueError(f"Chapter '{chapter.chapter_key}' has empty text.")
        sentences = _sentence_split(text)
        if not sentences:
            raise ValueError(f"Chapter '{chapter.chapter_key}' has no sentence-like content.")
        tokens = _tokenize(text)
        if not tokens:
            raise ValueError(f"Chapter '{chapter.chapter_key}' has no tokenizable content.")
        avg_sentence_length = len(tokens) / len(sentences)
        rows.append(
            ChapterFeatureRow(
                schema_version=FEATURE_SCHEMA_VERSION,
                story_id=normalized_story_id,
                chapter_key=chapter.chapter_key,
                chapter_index=index,
                source_length_chars=len(text),
                sentence_count=len(sentences),
                token_count=len(tokens),
                avg_sentence_length=round(avg_sentence_length, 4),
                dialogue_line_ratio=round(_dialogue_line_ratio(text), 4),
                top_keywords=_top_keywords(tokens),
            )
        )

    return StoryFeatureExtractionResult(
        schema_version=FEATURE_SCHEMA_VERSION,
        story_id=normalized_story_id,
        extracted_at_utc=datetime.now(UTC).isoformat(),
        chapter_features=rows,
    )
