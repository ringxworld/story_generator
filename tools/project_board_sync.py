"""Synchronize active roadmap issues and open PRs into a GitHub Project board."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, cast

REPO_ROOT = Path(__file__).resolve().parents[1]
WINDOWS_GH_PATH = Path(r"C:\Program Files\GitHub CLI\gh.exe")


class ProjectBoardSyncError(RuntimeError):
    """Raised when the project board sync cannot proceed."""


def _resolve_gh_binary() -> str:
    if configured := os.environ.get("GH_BIN"):
        candidate = Path(configured)
        if candidate.exists():
            return str(candidate)
        raise ProjectBoardSyncError(f"GH_BIN points to missing executable: {candidate}")
    if found := shutil.which("gh"):
        return found
    if os.name == "nt" and WINDOWS_GH_PATH.exists():
        return str(WINDOWS_GH_PATH)
    raise ProjectBoardSyncError("GitHub CLI executable not found. Install `gh` or set GH_BIN.")


def _run_gh_json(*args: str) -> Any:
    completed = subprocess.run(
        [_resolve_gh_binary(), *args],
        check=False,
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "gh command failed"
        raise ProjectBoardSyncError(message)
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise ProjectBoardSyncError("Unable to parse GitHub CLI JSON output.") from error


def _run_gh(*args: str) -> None:
    completed = subprocess.run(
        [_resolve_gh_binary(), *args],
        check=False,
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "gh command failed"
        raise ProjectBoardSyncError(message)


def _collect_board_urls(*, owner: str, project_number: int) -> set[str]:
    payload = cast(
        dict[str, Any],
        _run_gh_json(
            "project",
            "item-list",
            str(project_number),
            "--owner",
            owner,
            "--limit",
            "500",
            "--format",
            "json",
        ),
    )
    urls: set[str] = set()
    for item in cast(list[dict[str, Any]], payload.get("items", [])):
        content = cast(dict[str, Any], item.get("content", {}))
        url = content.get("url")
        if isinstance(url, str) and url.strip():
            urls.add(url.strip())
    return urls


def _get_project_id(*, owner: str, project_number: int) -> str:
    payload = cast(
        dict[str, Any],
        _run_gh_json(
            "project",
            "view",
            str(project_number),
            "--owner",
            owner,
            "--format",
            "json",
        ),
    )
    project_id = payload.get("id")
    if not isinstance(project_id, str) or not project_id.strip():
        raise ProjectBoardSyncError("Unable to resolve project ID.")
    return project_id.strip()


def _get_project_fields(*, owner: str, project_number: int) -> dict[str, dict[str, str]]:
    payload = cast(
        dict[str, Any],
        _run_gh_json(
            "project",
            "field-list",
            str(project_number),
            "--owner",
            owner,
            "--format",
            "json",
        ),
    )
    fields = cast(list[dict[str, Any]], payload.get("fields", []))
    mapping: dict[str, dict[str, str]] = {}
    for field in fields:
        name = str(field.get("name", "")).strip()
        if not name:
            continue
        field_id = str(field.get("id", "")).strip()
        if not field_id:
            continue
        options = cast(list[dict[str, Any]], field.get("options", []))
        option_map = {
            str(option.get("name", "")).strip(): str(option.get("id", "")).strip()
            for option in options
            if str(option.get("name", "")).strip() and str(option.get("id", "")).strip()
        }
        mapping[name] = {"id": field_id, **{f"option:{k}": v for k, v in option_map.items()}}
    return mapping


def _collect_project_items(*, owner: str, project_number: int) -> list[dict[str, Any]]:
    payload = cast(
        dict[str, Any],
        _run_gh_json(
            "project",
            "item-list",
            str(project_number),
            "--owner",
            owner,
            "--limit",
            "500",
            "--format",
            "json",
        ),
    )
    return cast(list[dict[str, Any]], payload.get("items", []))


def _collect_open_roadmap_issue_urls(*, repo: str, roadmap_label: str) -> set[str]:
    payload = cast(
        list[dict[str, Any]],
        _run_gh_json(
            "issue",
            "list",
            "--repo",
            repo,
            "--state",
            "open",
            "--limit",
            "500",
            "--json",
            "url,labels",
        ),
    )
    urls: set[str] = set()
    for issue in payload:
        labels = cast(list[dict[str, Any]], issue.get("labels", []))
        has_roadmap = any(str(label.get("name", "")).strip() == roadmap_label for label in labels)
        if not has_roadmap:
            continue
        url = issue.get("url")
        if isinstance(url, str) and url.strip():
            urls.add(url.strip())
    return urls


def _collect_open_pr_targets(*, repo: str) -> tuple[set[str], set[str]]:
    payload = cast(
        list[dict[str, Any]],
        _run_gh_json(
            "pr",
            "list",
            "--repo",
            repo,
            "--state",
            "open",
            "--limit",
            "500",
            "--json",
            "url,closingIssuesReferences",
        ),
    )
    pr_urls: set[str] = set()
    linked_issue_urls: set[str] = set()
    for pr in payload:
        pr_url = pr.get("url")
        if isinstance(pr_url, str) and pr_url.strip():
            pr_urls.add(pr_url.strip())
        closing_refs = cast(list[dict[str, Any]], pr.get("closingIssuesReferences", []))
        for reference in closing_refs:
            issue_url = reference.get("url")
            if isinstance(issue_url, str) and issue_url.strip():
                linked_issue_urls.add(issue_url.strip())
    return pr_urls, linked_issue_urls


def _sync_urls(
    *, owner: str, project_number: int, target_urls: set[str], board_urls: set[str]
) -> int:
    added = 0
    for url in sorted(target_urls):
        if url in board_urls:
            continue
        _run_gh(
            "project",
            "item-add",
            str(project_number),
            "--owner",
            owner,
            "--url",
            url,
        )
        added += 1
    return added


def _derive_priority_band(labels: set[str]) -> str | None:
    for candidate in ("Critical", "High", "Medium", "Low"):
        if f"Priority: {candidate}" in labels:
            return candidate
    return None


def _derive_track(labels: set[str]) -> str | None:
    if "Area: Dashboard" in labels:
        return "Dashboard"
    if "Area: Pipeline" in labels:
        return "Pipeline"
    if {"Area: NLP", "Area: QA", "Area: Data"} & labels:
        return "Platform"
    if "Docs" in labels:
        return "Docs"
    return None


def _set_single_select_field(
    *,
    item_id: str,
    project_id: str,
    field_id: str,
    option_id: str,
) -> None:
    _run_gh(
        "project",
        "item-edit",
        "--id",
        item_id,
        "--project-id",
        project_id,
        "--field-id",
        field_id,
        "--single-select-option-id",
        option_id,
    )


def _fill_roadmap_fields(
    *,
    owner: str,
    project_number: int,
    project_id: str,
    roadmap_label: str,
    field_map: dict[str, dict[str, str]],
) -> int:
    track_field = field_map.get("Track")
    priority_field = field_map.get("Priority Band")
    if not track_field or not priority_field:
        raise ProjectBoardSyncError("Project is missing Track/Priority Band single-select fields.")

    items = _collect_project_items(owner=owner, project_number=project_number)
    edits = 0
    for item in items:
        content = cast(dict[str, Any], item.get("content", {}))
        if str(content.get("type", "")) != "Issue":
            continue
        labels = {str(label).strip() for label in cast(list[str], item.get("labels", [])) if label}
        if roadmap_label not in labels:
            continue

        item_id = str(item.get("id", "")).strip()
        if not item_id:
            continue

        current_track = str(item.get("track", "")).strip()
        current_priority = str(item.get("priority Band", "")).strip()

        desired_track = _derive_track(labels)
        desired_priority = _derive_priority_band(labels)

        if not current_track and desired_track:
            option_id = track_field.get(f"option:{desired_track}", "")
            if option_id:
                _set_single_select_field(
                    item_id=item_id,
                    project_id=project_id,
                    field_id=track_field["id"],
                    option_id=option_id,
                )
                edits += 1

        if not current_priority and desired_priority:
            option_id = priority_field.get(f"option:{desired_priority}", "")
            if option_id:
                _set_single_select_field(
                    item_id=item_id,
                    project_id=project_id,
                    field_id=priority_field["id"],
                    option_id=option_id,
                )
                edits += 1
    return edits


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sync GitHub project board with active work.")
    parser.add_argument("--owner", required=True, help="GitHub owner (user/org).")
    parser.add_argument("--repo", required=True, help="Repository in owner/repo format.")
    parser.add_argument("--project-number", type=int, required=True, help="Project number.")
    parser.add_argument(
        "--roadmap-label",
        default="Roadmap",
        help="Issue label that marks roadmap-tracked issues.",
    )
    parser.add_argument(
        "--skip-field-fill",
        action="store_true",
        help="Skip filling missing Track/Priority Band on roadmap issue cards.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned additions without modifying project items.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    board_urls = _collect_board_urls(owner=args.owner, project_number=args.project_number)
    roadmap_issue_urls = _collect_open_roadmap_issue_urls(
        repo=args.repo, roadmap_label=args.roadmap_label
    )
    pr_urls, linked_issue_urls = _collect_open_pr_targets(repo=args.repo)
    target_urls = roadmap_issue_urls | linked_issue_urls | pr_urls
    missing_urls = sorted(url for url in target_urls if url not in board_urls)

    if args.dry_run:
        print("Project board sync dry-run")
        print("==========================")
        print(f"board items observed: {len(board_urls)}")
        print(f"target urls observed: {len(target_urls)}")
        print(f"would add: {len(missing_urls)}")
        print("field fill: skipped in dry-run")
        for url in missing_urls:
            print(url)
        return 0

    project_id = _get_project_id(owner=args.owner, project_number=args.project_number)
    field_map = _get_project_fields(owner=args.owner, project_number=args.project_number)
    added = _sync_urls(
        owner=args.owner,
        project_number=args.project_number,
        target_urls=target_urls,
        board_urls=board_urls,
    )
    field_edits = 0
    if not args.skip_field_fill:
        field_edits = _fill_roadmap_fields(
            owner=args.owner,
            project_number=args.project_number,
            project_id=project_id,
            roadmap_label=args.roadmap_label,
            field_map=field_map,
        )

    print("Project board sync")
    print("==================")
    print(f"board items observed: {len(board_urls)}")
    print(f"target urls observed: {len(target_urls)}")
    print(f"added: {added}")
    print(f"field edits: {field_edits}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ProjectBoardSyncError as error:
        print(error)
        raise SystemExit(1) from error
