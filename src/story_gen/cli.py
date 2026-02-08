"""CLI entry point for story_gen."""

from __future__ import annotations

from story_gen.application.planning import DependencyPlanner
from story_gen.domain.models import Chapter, Character, StoryBible, Theme


def main() -> None:
    bible = StoryBible(
        premise="A city learns its history was rewritten by a hidden council.",
        themes=(
            Theme(key="memory", statement="Memory can be engineered."),
            Theme(key="trust", statement="Trust must be earned, then re-earned."),
        ),
        characters=(
            Character(
                key="rhea",
                role="investigator",
                motivation="Find out why her brother vanished from records.",
            ),
            Character(
                key="ion",
                role="archivist",
                motivation="Protect the archive while revealing partial truths.",
            ),
        ),
        canon_rules=(
            "No supernatural causes are allowed.",
            "The council has exactly seven members.",
        ),
    )

    chapters = [
        Chapter(
            key="ch01",
            title="The Missing Ledger",
            objective="Introduce the disappearance and first contradiction.",
            required_themes=("memory",),
            participating_characters=("rhea", "ion"),
        ),
        Chapter(
            key="ch02",
            title="Audit at Dusk",
            objective="Raise the stakes with institutional resistance.",
            required_themes=("memory", "trust"),
            participating_characters=("rhea",),
            prerequisites=("ch01",),
        ),
    ]

    planner = DependencyPlanner()
    issues = planner.validate_chapter_dependencies(chapters)
    concept_map = planner.concept_dependency_map(bible, chapters)

    print("story_gen scaffold")
    print(f"premise: {bible.premise}")
    print(f"chapters: {len(chapters)}")
    print(f"dependency issues: {issues if issues else 'none'}")
    print("concept dependencies:")
    for source, targets in sorted(concept_map.items()):
        print(f"  {source} -> {sorted(targets)}")


if __name__ == "__main__":
    main()
