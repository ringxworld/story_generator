"""Ports for planner, drift checks, and persistence."""

from __future__ import annotations

from typing import Protocol

from story_gen.domain.models import Chapter, StoryBible, StoryState


class ChapterPlanner(Protocol):
    """Creates chapter plans from a story bible."""

    def plan_chapters(self, bible: StoryBible) -> list[Chapter]:
        ...


class DriftChecker(Protocol):
    """Checks a chapter against canon and continuity constraints."""

    def validate_chapter(self, chapter: Chapter, state: StoryState) -> list[str]:
        ...


class StoryRepository(Protocol):
    """Persists and loads story state."""

    def save(self, state: StoryState) -> None:
        ...

    def load(self) -> StoryState:
        ...
