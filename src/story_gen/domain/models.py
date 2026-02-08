"""Core story domain models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Theme:
    """A thematic signal that should appear in one or more chapters."""

    key: str
    statement: str
    priority: int = 1


@dataclass(frozen=True)
class Character:
    """A story character with stable traits and voice constraints."""

    key: str
    role: str
    motivation: str
    voice_markers: tuple[str, ...] = ()
    relationships: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Chapter:
    """A planned chapter with explicit dependencies and concept requirements."""

    key: str
    title: str
    objective: str
    required_themes: tuple[str, ...] = ()
    participating_characters: tuple[str, ...] = ()
    prerequisites: tuple[str, ...] = ()
    draft_text: str | None = None


@dataclass(frozen=True)
class StoryBible:
    """Canonical definitions that generated chapters must respect."""

    premise: str
    themes: tuple[Theme, ...]
    characters: tuple[Character, ...]
    canon_rules: tuple[str, ...] = ()

    def theme_keys(self) -> set[str]:
        return {theme.key for theme in self.themes}

    def character_keys(self) -> set[str]:
        return {character.key for character in self.characters}


@dataclass
class StoryState:
    """Mutable story state as chapters are generated and validated."""

    bible: StoryBible
    chapters: list[Chapter] = field(default_factory=list)
    open_threads: list[str] = field(default_factory=list)
    resolved_threads: list[str] = field(default_factory=list)

    def add_chapter(self, chapter: Chapter) -> None:
        self.chapters.append(chapter)

    def chapter_order_is_valid(self) -> bool:
        seen: set[str] = set()
        for chapter in self.chapters:
            if not set(chapter.prerequisites).issubset(seen):
                return False
            seen.add(chapter.key)
        return True
