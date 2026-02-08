from __future__ import annotations

from story_gen.core.essay_quality import (
    EssayDraftInput,
    EssayPolicySpec,
    EssaySectionSpec,
    evaluate_essay_quality,
)


def _policy() -> EssayPolicySpec:
    return EssayPolicySpec(
        thesis_statement="Constraint-first drafting improves coherence.",
        audience="technical readers",
        tone="analytical",
        min_words=30,
        max_words=400,
        required_sections=(
            EssaySectionSpec(key="introduction", purpose="Frame claim", min_paragraphs=1),
            EssaySectionSpec(key="analysis", purpose="Develop claim", min_paragraphs=1),
            EssaySectionSpec(key="conclusion", purpose="Close claim", min_paragraphs=1),
        ),
        banned_phrases=("as an ai language model",),
        required_citations=1,
    )


def test_evaluate_essay_quality_passes_good_draft() -> None:
    draft = EssayDraftInput(
        title="Constraint Drafting",
        prompt="Explain why guardrails help.",
        draft_text=(
            "introduction: Constraint-first drafting improves coherence and limits drift.\n\n"
            "analysis: according to [1], fixed checks improve consistency and quality in long revisions.\n\n"
            "conclusion: constraint-first workflows stay readable and maintain stable arguments."
        ),
        policy=_policy(),
    )
    result = evaluate_essay_quality(draft)
    assert result.passed is True
    assert result.score == 100.0
    assert result.checks == ()


def test_evaluate_essay_quality_reports_failures() -> None:
    draft = EssayDraftInput(
        title="Bad Draft",
        prompt="Explain why guardrails help.",
        draft_text="analysis: as an ai language model I cannot cite sources.",
        policy=_policy(),
    )
    result = evaluate_essay_quality(draft)
    assert result.passed is False
    assert result.score < 100.0
    codes = {check.code for check in result.checks}
    assert "word_count_out_of_range" in codes
    assert "insufficient_citations" in codes
    assert "banned_phrase_present" in codes
    assert "missing_required_section" in codes
