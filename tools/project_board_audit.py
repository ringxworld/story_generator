"""Audit GitHub Project board hygiene for roadmap triage."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

WINDOWS_GH_PATH = Path(r"C:\Program Files\GitHub CLI\gh.exe")


@dataclass(frozen=True)
class AuditResult:
    errors: list[str]
    warnings: list[str]
    notes: list[str]


class ProjectBoardAuditError(RuntimeError):
    """Raised when project board audit cannot execute."""


def _resolve_gh_binary() -> str:
    if configured := os.environ.get("GH_BIN"):
        candidate = Path(configured)
        if candidate.exists():
            return str(candidate)
        raise ProjectBoardAuditError(f"GH_BIN points to missing executable: {candidate}")
    if found := shutil.which("gh"):
        return found
    if os.name == "nt" and WINDOWS_GH_PATH.exists():
        return str(WINDOWS_GH_PATH)
    raise ProjectBoardAuditError("GitHub CLI executable not found. Install `gh` or set GH_BIN.")


def _run_gh_json(args: list[str]) -> dict[str, Any]:
    gh_bin = _resolve_gh_binary()
    completed = subprocess.run(
        [gh_bin, *args],
        check=False,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "gh command failed"
        raise RuntimeError(message)
    return cast(dict[str, Any], json.loads(completed.stdout))


def _get_project_metadata(owner: str, project_number: int) -> dict[str, Any]:
    return _run_gh_json(
        [
            "project",
            "view",
            str(project_number),
            "--owner",
            owner,
            "--format",
            "json",
        ]
    )


def _get_project_fields(owner: str, project_number: int) -> list[dict[str, Any]]:
    payload = _run_gh_json(
        [
            "project",
            "field-list",
            str(project_number),
            "--owner",
            owner,
            "--format",
            "json",
        ]
    )
    return cast(list[dict[str, Any]], payload.get("fields", []))


def _get_project_items(owner: str, project_number: int) -> list[dict[str, Any]]:
    payload = _run_gh_json(
        [
            "project",
            "item-list",
            str(project_number),
            "--owner",
            owner,
            "--limit",
            "200",
            "--format",
            "json",
        ]
    )
    return cast(list[dict[str, Any]], payload.get("items", []))


def _get_project_view_names(project_number: int) -> list[str]:
    query = (
        "query($number:Int!){ viewer { projectV2(number:$number) "
        "{ views(first:20){ nodes { name } } } } }"
    )
    payload = _run_gh_json(
        [
            "api",
            "graphql",
            "--raw-field",
            f"query={query}",
            "-F",
            f"number={project_number}",
        ]
    )
    nodes = (
        payload.get("data", {})
        .get("viewer", {})
        .get("projectV2", {})
        .get("views", {})
        .get("nodes", [])
    )
    return [str(node.get("name", "")).strip() for node in nodes if node.get("name")]


def _has_manual_rename_step(readme: str) -> bool:
    lowered = readme.lower()
    return "view 1" in lowered and "rename" in lowered and "view options" in lowered


def evaluate_project_hygiene(
    *,
    title: str,
    description: str,
    readme: str,
    field_names: set[str],
    items: list[dict[str, Any]],
    view_names: list[str],
    roadmap_start: int,
    roadmap_end: int,
) -> AuditResult:
    errors: list[str] = []
    warnings: list[str] = []
    notes: list[str] = []

    if not title.strip():
        errors.append("Project title is empty.")
    if not description.strip():
        errors.append("Project description is empty.")
    if not readme.strip():
        errors.append("Project readme is empty.")

    for required in ("Track", "Priority Band", "Status"):
        if required not in field_names:
            errors.append(f"Missing triage field: {required}.")

    roadmap_item_count = 0
    roadmap_numbers_expected = set(range(roadmap_start, roadmap_end + 1))
    roadmap_numbers_seen: set[int] = set()

    for item in items:
        content = item.get("content") or {}
        number = content.get("number")
        labels = item.get("labels", [])
        is_roadmap = "Roadmap" in labels or (
            isinstance(number, int) and number in roadmap_numbers_expected
        )
        if not is_roadmap:
            continue
        roadmap_item_count += 1
        if isinstance(number, int):
            roadmap_numbers_seen.add(number)

        track = item.get("track")
        priority = item.get("priority Band")
        status = item.get("status")
        title_text = item.get("title", f"issue-{number}")
        if not track:
            errors.append(f"Roadmap item missing Track: {title_text}.")
        if not priority:
            errors.append(f"Roadmap item missing Priority Band: {title_text}.")
        if not status:
            errors.append(f"Roadmap item missing Status: {title_text}.")

    missing_expected = sorted(roadmap_numbers_expected - roadmap_numbers_seen)
    if missing_expected:
        warnings.append(
            "Expected roadmap issue numbers not found on board: "
            + ", ".join(str(number) for number in missing_expected)
        )

    if roadmap_item_count == 0:
        errors.append("No roadmap items detected on project board.")

    if any(name == "View 1" for name in view_names):
        if _has_manual_rename_step(readme):
            warnings.append(
                "Project view is still named 'View 1'; readme includes manual rename path."
            )
        else:
            errors.append(
                "Project view is still named 'View 1' and no manual rename step is documented."
            )

    notes.append(f"Roadmap items checked: {roadmap_item_count}")
    notes.append(f"Project views discovered: {', '.join(view_names) if view_names else 'none'}")
    return AuditResult(errors=errors, warnings=warnings, notes=notes)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit roadmap project board hygiene.")
    parser.add_argument("--owner", required=True, help="GitHub owner login (user/org).")
    parser.add_argument("--project-number", type=int, required=True, help="Project number.")
    parser.add_argument(
        "--roadmap-start", type=int, default=2, help="Inclusive start issue number."
    )
    parser.add_argument("--roadmap-end", type=int, default=11, help="Inclusive end issue number.")
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    metadata = _get_project_metadata(args.owner, args.project_number)
    fields = _get_project_fields(args.owner, args.project_number)
    items = _get_project_items(args.owner, args.project_number)
    views = _get_project_view_names(args.project_number)

    result = evaluate_project_hygiene(
        title=str(metadata.get("title", "")),
        description=str(metadata.get("shortDescription", "")),
        readme=str(metadata.get("readme", "")),
        field_names={str(field.get("name", "")).strip() for field in fields},
        items=items,
        view_names=views,
        roadmap_start=args.roadmap_start,
        roadmap_end=args.roadmap_end,
    )

    if args.format == "json":
        payload = {
            "errors": result.errors,
            "warnings": result.warnings,
            "notes": result.notes,
        }
        print(json.dumps(payload, indent=2))
    else:
        print("Project board audit")
        print("===================")
        for note in result.notes:
            print(f"note: {note}")
        for warning in result.warnings:
            print(f"warning: {warning}")
        for error in result.errors:
            print(f"error: {error}")

    return 1 if result.errors else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ProjectBoardAuditError as error:
        print(error)
        raise SystemExit(1) from error
