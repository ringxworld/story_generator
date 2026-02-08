from __future__ import annotations

import pytest

from story_gen.api.contracts import EssayBlueprint, StoryBlueprint


def test_contract_normalizes_keys_and_dedupes_lists() -> None:
    blueprint = StoryBlueprint.model_validate(
        {
            "premise": "  Premise  ",
            "themes": [{"key": "Memory", "statement": "Statement", "priority": 1}],
            "characters": [
                {
                    "key": "Rhea",
                    "role": "investigator",
                    "motivation": "Find truth",
                    "voice_markers": ["short", "short", " urgent "],
                    "relationships": {},
                }
            ],
            "chapters": [
                {
                    "key": "CH01",
                    "title": "T",
                    "objective": "O",
                    "required_themes": ["memory", "memory"],
                    "participating_characters": ["rhea", "rhea"],
                    "prerequisites": [],
                    "draft_text": None,
                }
            ],
            "canon_rules": [" rule ", "rule"],
        }
    )
    assert blueprint.themes[0].key == "memory"
    assert blueprint.characters[0].key == "rhea"
    assert blueprint.chapters[0].key == "ch01"
    assert blueprint.chapters[0].required_themes == ["memory"]
    assert blueprint.canon_rules == ["rule"]


def test_contract_rejects_unknown_relationship_target() -> None:
    with pytest.raises(ValueError, match="unknown characters"):
        StoryBlueprint.model_validate(
            {
                "premise": "Premise",
                "themes": [],
                "characters": [
                    {
                        "key": "rhea",
                        "role": "investigator",
                        "motivation": "Find truth",
                        "voice_markers": [],
                        "relationships": {"missing": "ally"},
                    }
                ],
                "chapters": [],
                "canon_rules": [],
            }
        )


def test_contract_rejects_chapter_cycle() -> None:
    with pytest.raises(ValueError, match="dependency cycle"):
        StoryBlueprint.model_validate(
            {
                "premise": "Premise",
                "themes": [{"key": "memory", "statement": "x", "priority": 1}],
                "characters": [
                    {
                        "key": "rhea",
                        "role": "investigator",
                        "motivation": "Find truth",
                        "voice_markers": [],
                        "relationships": {},
                    }
                ],
                "chapters": [
                    {
                        "key": "ch01",
                        "title": "1",
                        "objective": "1",
                        "required_themes": ["memory"],
                        "participating_characters": ["rhea"],
                        "prerequisites": ["ch02"],
                        "draft_text": None,
                    },
                    {
                        "key": "ch02",
                        "title": "2",
                        "objective": "2",
                        "required_themes": ["memory"],
                        "participating_characters": ["rhea"],
                        "prerequisites": ["ch01"],
                        "draft_text": None,
                    },
                ],
                "canon_rules": [],
            }
        )


def test_essay_contract_rejects_invalid_policy_ranges() -> None:
    with pytest.raises(ValueError, match="min_words < max_words"):
        EssayBlueprint.model_validate(
            {
                "prompt": "Write clearly.",
                "policy": {
                    "thesis_statement": "x",
                    "audience": "technical readers",
                    "tone": "analytical",
                    "min_words": 500,
                    "max_words": 300,
                    "required_sections": [],
                    "banned_phrases": [],
                    "required_citations": 0,
                },
                "rubric": [],
            }
        )


def test_essay_contract_normalizes_and_validates_section_keys() -> None:
    blueprint = EssayBlueprint.model_validate(
        {
            "prompt": "Write clearly.",
            "policy": {
                "thesis_statement": "Constraint-first drafting improves coherence.",
                "audience": "technical readers",
                "tone": "analytical",
                "min_words": 300,
                "max_words": 900,
                "required_sections": [
                    {
                        "key": "Introduction",
                        "purpose": "Frame claim",
                        "min_paragraphs": 1,
                        "required_terms": ["coherence", "coherence"],
                    }
                ],
                "banned_phrases": ["as an ai language model", "as an ai language model"],
                "required_citations": 1,
            },
            "rubric": ["clear thesis", "clear thesis"],
        }
    )
    assert blueprint.policy.required_sections[0].key == "introduction"
    assert blueprint.policy.required_sections[0].required_terms == ["coherence"]
    assert blueprint.policy.banned_phrases == ["as an ai language model"]
    assert blueprint.rubric == ["clear thesis"]
