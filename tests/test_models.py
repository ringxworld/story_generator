from story_gen.application.planning import DependencyPlanner
from story_gen.domain.models import Chapter, Character, StoryBible, StoryState, Theme


def test_story_state_chapter_order_valid() -> None:
    bible = StoryBible(
        premise="Premise",
        themes=(Theme(key="truth", statement="Truth has cost."),),
        characters=(Character(key="alex", role="lead", motivation="Find truth"),),
    )
    state = StoryState(bible=bible)
    state.add_chapter(Chapter(key="ch01", title="A", objective="Start"))
    state.add_chapter(
        Chapter(key="ch02", title="B", objective="Continue", prerequisites=("ch01",))
    )
    assert state.chapter_order_is_valid() is True


def test_dependency_planner_detects_unknown_prerequisite() -> None:
    planner = DependencyPlanner()
    chapters = [
        Chapter(
            key="ch01",
            title="A",
            objective="Start",
            prerequisites=("missing",),
        )
    ]

    issues = planner.validate_chapter_dependencies(chapters)
    assert len(issues) == 1
    assert "unknown prerequisite" in issues[0]


def test_dependency_planner_detects_cycle() -> None:
    planner = DependencyPlanner()
    chapters = [
        Chapter(key="ch01", title="A", objective="Start", prerequisites=("ch02",)),
        Chapter(key="ch02", title="B", objective="Continue", prerequisites=("ch01",)),
    ]

    issues = planner.validate_chapter_dependencies(chapters)
    assert any("cycle" in issue for issue in issues)
