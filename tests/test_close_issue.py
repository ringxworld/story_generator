from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "close_issue",
    Path(__file__).resolve().parents[1] / "tools" / "close_issue.py",
)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("Unable to load tools/close_issue.py")
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)
validate_summary = _MODULE.validate_summary


VALID_SUMMARY = """# Work Summary

## Objective
Resolve issue scope in pipeline while preserving API stability.

## Root Cause
Identified the fault introduced by parser refactor due to null guard removal.

## Approach
- Audited flow from API to extraction modules.
- Chose focused guard restoration over broad retry wrappers because less blast radius.
- Implemented fix in core parser module without public API changes.

## Implementation Details
- PR #100: restore null guard in parser.
- PR #101: add regression test for empty narrative stage.
- Commit abc123: remove duplicate fallback branch.

## Validation
- Added tests for baseline and malformed input.
- Verified compatibility with downstream contracts.
- Confirmed no regression with pytest and CI quality checks.

## Ownership / Follow-ups
- Change is contained within story pipeline.
- External action required: none.
- Deferred work tracked in https://github.com/ringxworld/story_generator/issues/999.
"""


def test_validate_summary_accepts_required_structure() -> None:
    assert validate_summary(VALID_SUMMARY) == []


def test_validate_summary_rejects_missing_sections() -> None:
    missing_root_cause = VALID_SUMMARY.replace("## Root Cause", "## Source")
    problems = validate_summary(missing_root_cause)
    assert "Root Cause" in problems


def test_validate_summary_rejects_placeholder_tokens() -> None:
    with_placeholder = VALID_SUMMARY.replace("pipeline", "<component>")
    problems = validate_summary(with_placeholder)
    assert any("Replace placeholder tokens" in problem for problem in problems)


def test_validate_summary_accepts_utf8_bom_prefix() -> None:
    problems = validate_summary("\ufeff" + VALID_SUMMARY)
    assert problems == []
