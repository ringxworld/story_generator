"""Detect and repair escaped-newline formatting in GitHub issue bodies."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

REPO_ROOT = Path(__file__).resolve().parents[1]
WINDOWS_GH_PATH = Path(r"C:\Program Files\GitHub CLI\gh.exe")


class IssueBodyHygieneError(RuntimeError):
    """Raised when issue body hygiene operations fail."""


@dataclass(frozen=True)
class IssueRecord:
    number: int
    title: str
    state: str
    body: str
    url: str


@dataclass(frozen=True)
class IssueFix:
    issue: IssueRecord
    normalized_body: str


def _resolve_gh_binary() -> str:
    if configured := os.environ.get("GH_BIN"):
        candidate = Path(configured)
        if candidate.exists():
            return str(candidate)
        raise IssueBodyHygieneError(f"GH_BIN points to missing executable: {candidate}")
    if found := shutil.which("gh"):
        return found
    if os.name == "nt" and WINDOWS_GH_PATH.exists():
        return str(WINDOWS_GH_PATH)
    raise IssueBodyHygieneError("GitHub CLI executable not found. Install `gh` or set GH_BIN.")


def _run_gh_json(args: list[str]) -> Any:
    completed = subprocess.run(
        [_resolve_gh_binary(), *args],
        check=False,
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "gh command failed"
        raise IssueBodyHygieneError(message)
    return json.loads(completed.stdout)


def _run_gh(args: list[str]) -> None:
    completed = subprocess.run(
        [_resolve_gh_binary(), *args],
        check=False,
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "gh command failed"
        raise IssueBodyHygieneError(message)


def has_escaped_newline_formatting(body: str) -> bool:
    if "\\n" not in body and "\\r\\n" not in body:
        return False

    literal_count = body.count("\\n") + body.count("\\r\\n")
    real_count = body.count("\n")
    has_template_signals = "## " in body and "\\n" in body
    has_list_signals = "\\n- " in body

    if real_count == 0:
        return True
    if literal_count >= real_count and (has_template_signals or has_list_signals):
        return True
    return False


def normalize_issue_body(body: str) -> str:
    normalized = body.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\r\n", "\n")
    normalized = "\n".join(line.rstrip() for line in normalized.split("\n"))
    return normalized.strip() + "\n"


def collect_issues(
    *, repo: str, issue_numbers: list[int], state: str, limit: int
) -> list[IssueRecord]:
    if issue_numbers:
        issues: list[IssueRecord] = []
        for number in issue_numbers:
            payload = cast(
                dict[str, Any],
                _run_gh_json(
                    [
                        "issue",
                        "view",
                        str(number),
                        "--repo",
                        repo,
                        "--json",
                        "number,title,state,body,url",
                    ]
                ),
            )
            issues.append(
                IssueRecord(
                    number=int(payload["number"]),
                    title=str(payload.get("title", "")),
                    state=str(payload.get("state", "")),
                    body=str(payload.get("body", "")),
                    url=str(payload.get("url", "")),
                )
            )
        return issues

    payload = cast(
        list[dict[str, Any]],
        _run_gh_json(
            [
                "issue",
                "list",
                "--repo",
                repo,
                "--state",
                state,
                "--limit",
                str(limit),
                "--json",
                "number,title,state,body,url",
            ]
        ),
    )
    return [
        IssueRecord(
            number=int(item["number"]),
            title=str(item.get("title", "")),
            state=str(item.get("state", "")),
            body=str(item.get("body", "")),
            url=str(item.get("url", "")),
        )
        for item in payload
    ]


def plan_issue_fixes(issues: list[IssueRecord]) -> list[IssueFix]:
    fixes: list[IssueFix] = []
    for issue in issues:
        if not has_escaped_newline_formatting(issue.body):
            continue
        normalized = normalize_issue_body(issue.body)
        if normalized == issue.body:
            continue
        fixes.append(IssueFix(issue=issue, normalized_body=normalized))
    return fixes


def apply_issue_fixes(*, repo: str, fixes: list[IssueFix]) -> None:
    for fix in fixes:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", suffix=".md", delete=False
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(fix.normalized_body)
        try:
            _run_gh(
                [
                    "issue",
                    "edit",
                    str(fix.issue.number),
                    "--repo",
                    repo,
                    "--body-file",
                    str(temp_path),
                ]
            )
        finally:
            temp_path.unlink(missing_ok=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Detect/repair escaped-newline issue body formatting."
    )
    parser.add_argument("--repo", required=True, help="Repository in owner/repo format.")
    parser.add_argument(
        "--issues", nargs="*", type=int, default=[], help="Issue numbers to inspect."
    )
    parser.add_argument(
        "--state",
        default="all",
        choices=("open", "closed", "all"),
        help="Issue state when scanning via issue list.",
    )
    parser.add_argument(
        "--limit", type=int, default=200, help="Max issues to scan when --issues is omitted."
    )
    parser.add_argument(
        "--apply", action="store_true", help="Apply fixes in-place on GitHub issues."
    )
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format.")
    return parser


def _print_text(*, fixes: list[IssueFix], applied: bool) -> None:
    mode = "applied" if applied else "dry-run"
    print(f"Issue body hygiene ({mode})")
    print("========================")
    print(f"fixes: {len(fixes)}")
    for fix in fixes:
        print(f"- #{fix.issue.number} {fix.issue.title}")


def _print_json(*, fixes: list[IssueFix], applied: bool) -> None:
    payload = {
        "mode": "applied" if applied else "dry-run",
        "fixes": [
            {
                "number": fix.issue.number,
                "title": fix.issue.title,
                "state": fix.issue.state,
                "url": fix.issue.url,
            }
            for fix in fixes
        ],
    }
    print(json.dumps(payload, indent=2))


def main() -> int:
    args = build_parser().parse_args()
    issues = collect_issues(
        repo=args.repo, issue_numbers=args.issues, state=args.state, limit=args.limit
    )
    fixes = plan_issue_fixes(issues)

    if args.apply and fixes:
        apply_issue_fixes(repo=args.repo, fixes=fixes)

    if args.format == "json":
        _print_json(fixes=fixes, applied=args.apply)
    else:
        _print_text(fixes=fixes, applied=args.apply)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except IssueBodyHygieneError as error:
        print(error)
        raise SystemExit(1) from error
