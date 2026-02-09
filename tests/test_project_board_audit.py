from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

_SPEC = importlib.util.spec_from_file_location(
    "project_board_audit",
    Path(__file__).resolve().parents[1] / "tools" / "project_board_audit.py",
)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("Unable to load tools/project_board_audit.py")
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)
evaluate_project_hygiene = _MODULE.evaluate_project_hygiene


def _roadmap_item(
    number: int,
    *,
    track: str | None = "Pipeline",
    priority: str | None = "High",
) -> dict[str, object]:
    return {
        "content": {"number": number},
        "labels": ["Roadmap"],
        "title": f"Issue {number}",
        "track": track,
        "priority Band": priority,
    }


def test_evaluate_project_hygiene_passes_with_manual_view_rename_note() -> None:
    result = evaluate_project_hygiene(
        title="Story Generator Roadmap Board",
        description="Roadmap Kanban for issue triage and delivery flow.",
        readme="View 1 can be renamed via View options (...) -> Rename.",
        field_names={"Track", "Priority Band", "Status"},
        items=[_roadmap_item(number) for number in range(2, 12)],
        view_names=["View 1"],
        roadmap_start=2,
        roadmap_end=11,
    )

    assert result.errors == []
    assert any("manual rename path" in warning for warning in result.warnings)


def test_evaluate_project_hygiene_fails_when_required_field_missing() -> None:
    result = evaluate_project_hygiene(
        title="Story Generator Roadmap Board",
        description="Roadmap Kanban for issue triage and delivery flow.",
        readme="View 1 can be renamed via View options (...) -> Rename.",
        field_names={"Track", "Status"},
        items=[_roadmap_item(number) for number in range(2, 12)],
        view_names=["Roadmap Board"],
        roadmap_start=2,
        roadmap_end=11,
    )

    assert "Missing triage field: Priority Band." in result.errors


def test_evaluate_project_hygiene_fails_for_missing_roadmap_values() -> None:
    items = [_roadmap_item(number) for number in range(2, 12)]
    items[0]["track"] = None
    items[1]["priority Band"] = None

    result = evaluate_project_hygiene(
        title="Story Generator Roadmap Board",
        description="Roadmap Kanban for issue triage and delivery flow.",
        readme="View 1 can be renamed via View options (...) -> Rename.",
        field_names={"Track", "Priority Band", "Status"},
        items=items,
        view_names=["Roadmap Board"],
        roadmap_start=2,
        roadmap_end=11,
    )

    assert any("missing Track" in error for error in result.errors)
    assert any("missing Priority Band" in error for error in result.errors)


def test_evaluate_project_hygiene_requires_manual_step_when_view_placeholder_exists() -> None:
    result = evaluate_project_hygiene(
        title="Story Generator Roadmap Board",
        description="Roadmap Kanban for issue triage and delivery flow.",
        readme="Project workflow only.",
        field_names={"Track", "Priority Band", "Status"},
        items=[_roadmap_item(number) for number in range(2, 12)],
        view_names=["View 1"],
        roadmap_start=2,
        roadmap_end=11,
    )

    assert any("no manual rename step is documented" in error for error in result.errors)
