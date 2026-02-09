from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "tools" / "issue_body_hygiene.py"


def _load_module() -> Any:
    spec = importlib.util.spec_from_file_location("issue_body_hygiene", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_detects_escaped_newline_issue_body() -> None:
    module = _load_module()
    body = "## Summary\\nLine one\\n\\n## Acceptance\\n- Item"
    assert module.has_escaped_newline_formatting(body) is True


def test_ignores_normal_markdown_newlines() -> None:
    module = _load_module()
    body = "## Summary\nLine one\n\n## Acceptance\n- Item"
    assert module.has_escaped_newline_formatting(body) is False


def test_normalize_issue_body_rewrites_literals() -> None:
    module = _load_module()
    raw = "## Summary\\nLine one\\n\\n## Acceptance\\n- Item"
    normalized = module.normalize_issue_body(raw)
    assert normalized == "## Summary\nLine one\n\n## Acceptance\n- Item\n"


def test_plan_issue_fixes_only_returns_malformed_issues() -> None:
    module = _load_module()
    issues = [
        module.IssueRecord(
            number=104,
            title="Broken",
            state="OPEN",
            body="## Summary\\nBroken body",
            url="https://example.invalid/104",
        ),
        module.IssueRecord(
            number=105,
            title="Good",
            state="OPEN",
            body="## Summary\nGood body",
            url="https://example.invalid/105",
        ),
    ]

    fixes = module.plan_issue_fixes(issues)

    assert len(fixes) == 1
    assert fixes[0].issue.number == 104
    assert "\\n" not in fixes[0].normalized_body
