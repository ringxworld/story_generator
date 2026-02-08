"""Planning services that map concepts and chapter dependencies."""

from __future__ import annotations

from collections import defaultdict

from story_gen.domain.models import Chapter, StoryBible


class DependencyPlanner:
    """Computes dependency views used to guide concrete implementations."""

    def chapter_dependency_graph(self, chapters: list[Chapter]) -> dict[str, set[str]]:
        graph: dict[str, set[str]] = {}
        for chapter in chapters:
            graph[chapter.key] = set(chapter.prerequisites)
        return graph

    def concept_dependency_map(
        self, bible: StoryBible, chapters: list[Chapter]
    ) -> dict[str, set[str]]:
        mapping: dict[str, set[str]] = defaultdict(set)
        theme_keys = bible.theme_keys()
        character_keys = bible.character_keys()

        for chapter in chapters:
            for theme in chapter.required_themes:
                if theme in theme_keys:
                    mapping[f"theme:{theme}"].add(f"chapter:{chapter.key}")
            for character in chapter.participating_characters:
                if character in character_keys:
                    mapping[f"character:{character}"].add(f"chapter:{chapter.key}")
        return dict(mapping)

    def validate_chapter_dependencies(self, chapters: list[Chapter]) -> list[str]:
        issues: list[str] = []
        known = {chapter.key for chapter in chapters}

        for chapter in chapters:
            for prerequisite in chapter.prerequisites:
                if prerequisite not in known:
                    issues.append(
                        f"Chapter '{chapter.key}' references unknown prerequisite '{prerequisite}'."
                    )

        graph = self.chapter_dependency_graph(chapters)
        if self._has_cycle(graph):
            issues.append("Chapter dependency graph contains at least one cycle.")
        return issues

    def _has_cycle(self, graph: dict[str, set[str]]) -> bool:
        temporary: set[str] = set()
        permanent: set[str] = set()

        def visit(node: str) -> bool:
            if node in permanent:
                return False
            if node in temporary:
                return True

            temporary.add(node)
            for dependency in graph.get(node, set()):
                if dependency in graph and visit(dependency):
                    return True
            temporary.remove(node)
            permanent.add(node)
            return False

        return any(visit(node) for node in graph if node not in permanent)
