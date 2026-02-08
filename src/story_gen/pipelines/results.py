"""Typed result objects returned by workflow pipelines."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StoryCollectionResult:
    """Filesystem outputs produced by story collection."""

    output_root: Path
    full_story_path: Path
    index_path: Path
    chapter_count: int


@dataclass(frozen=True)
class VideoStoryResult:
    """Media and transcript outputs produced by the video workflow."""

    output_dir: Path
    audio_path: Path
    transcript_path: Path | None
