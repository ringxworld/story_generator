"""Automate PR opening, status waiting, and merging with GitHub CLI."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PR_TEMPLATE_PATH = REPO_ROOT / ".github" / "pull_request_template.md"
PROTECTED_BRANCHES = {"main", "develop"}
WINDOWS_GH_PATH = Path(r"C:\Program Files\GitHub CLI\gh.exe")
DEFAULT_REVIEWER = "ringxworld"


class PrFlowError(RuntimeError):
    """Raised when automated PR flow cannot proceed."""


@dataclass(frozen=True)
class PullRequestRef:
    """Stable reference for one pull request."""

    number: int
    url: str


def _resolve_gh_binary() -> str:
    if configured := os.environ.get("GH_BIN"):
        candidate = Path(configured)
        if candidate.exists():
            return str(candidate)
        raise PrFlowError(f"GH_BIN points to missing executable: {candidate}")

    if found := shutil.which("gh"):
        return found

    if os.name == "nt" and WINDOWS_GH_PATH.exists():
        return str(WINDOWS_GH_PATH)

    raise PrFlowError(
        "GitHub CLI executable not found. Install `gh`, set GH_BIN, or add it to PATH."
    )


def _run(command: list[str], *, capture_output: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=False,
        text=True,
        capture_output=capture_output,
        cwd=REPO_ROOT,
    )


def _run_or_raise(
    command: list[str], *, capture_output: bool = False
) -> subprocess.CompletedProcess[str]:
    completed = _run(command, capture_output=capture_output)
    if completed.returncode != 0:
        stderr = completed.stderr.strip() if completed.stderr else ""
        stdout = completed.stdout.strip() if completed.stdout else ""
        message = stderr or stdout or f"command failed: {' '.join(command)}"
        raise PrFlowError(message)
    return completed


def _current_branch() -> str:
    completed = _run_or_raise(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
    )
    return completed.stdout.strip()


def _default_title_for_branch(branch: str) -> str:
    cleaned = branch.replace("_", " ").replace("-", " ").strip()
    if cleaned:
        return cleaned[:1].upper() + cleaned[1:]
    return "Update"


def _ensure_feature_branch() -> str:
    branch = _current_branch()
    if branch in PROTECTED_BRANCHES:
        raise PrFlowError("Run PR automation from a feature branch, not develop/main.")
    return branch


def _resolve_current_pr() -> PullRequestRef | None:
    completed = _run(
        [_resolve_gh_binary(), "pr", "view", "--json", "number,url"],
        capture_output=True,
    )
    if completed.returncode != 0:
        return None
    import json

    payload = json.loads(completed.stdout)
    return PullRequestRef(number=int(payload["number"]), url=str(payload["url"]))


def _resolve_pr_ref(explicit: str | None) -> str:
    if explicit:
        return explicit
    current = _resolve_current_pr()
    if current is None:
        raise PrFlowError("No pull request found for current branch. Open one first.")
    return str(current.number)


def _resolve_default_reviewer() -> str | None:
    reviewer = os.environ.get("PR_DEFAULT_REVIEWER", DEFAULT_REVIEWER).strip()
    return reviewer or None


def _normalize_reviewers(reviewers: list[str] | None) -> list[str]:
    if reviewers:
        cleaned = [reviewer.strip() for reviewer in reviewers if reviewer.strip()]
    else:
        default_reviewer = _resolve_default_reviewer()
        cleaned = [default_reviewer] if default_reviewer else []

    deduped: list[str] = []
    for reviewer in cleaned:
        if reviewer not in deduped:
            deduped.append(reviewer)
    return deduped


def _request_reviewers(*, pr_ref: str, reviewers: list[str]) -> None:
    if not reviewers:
        return

    gh = _resolve_gh_binary()
    for reviewer in reviewers:
        review_request = _run(
            [gh, "pr", "edit", pr_ref, "--add-reviewer", reviewer],
            capture_output=True,
        )
        if review_request.returncode == 0:
            print(f"Requested reviewer '{reviewer}' on PR {pr_ref}.")
            continue

        stderr = review_request.stderr.strip() if review_request.stderr else ""
        stdout = review_request.stdout.strip() if review_request.stdout else ""
        message = stderr or stdout or "unknown error while adding reviewer"
        print(f"Reviewer request skipped for '{reviewer}' on PR {pr_ref}: {message}")

        # GitHub does not allow requesting review from the PR author. Fallback to assignee.
        if "author" in message.lower():
            assignee_request = _run(
                [gh, "pr", "edit", pr_ref, "--add-assignee", reviewer],
                capture_output=True,
            )
            if assignee_request.returncode == 0:
                print(f"Added '{reviewer}' as assignee on PR {pr_ref}.")


def open_pr(*, base: str, title: str | None, reviewers: list[str] | None) -> PullRequestRef:
    branch = _ensure_feature_branch()
    selected_reviewers = _normalize_reviewers(reviewers)
    existing = _resolve_current_pr()
    if existing is not None:
        _request_reviewers(pr_ref=str(existing.number), reviewers=selected_reviewers)
        print(f"PR already exists: {existing.url}")
        return existing

    if not PR_TEMPLATE_PATH.exists():
        raise PrFlowError(f"Missing PR template file: {PR_TEMPLATE_PATH}")

    effective_title = (
        title.strip() if title and title.strip() else _default_title_for_branch(branch)
    )
    completed = _run_or_raise(
        [
            _resolve_gh_binary(),
            "pr",
            "create",
            "--base",
            base,
            "--head",
            branch,
            "--title",
            effective_title,
            "--body-file",
            str(PR_TEMPLATE_PATH),
        ],
        capture_output=True,
    )
    url = completed.stdout.strip().splitlines()[-1]
    print(f"Opened PR: {url}")
    resolved = _resolve_current_pr()
    if resolved is None:
        raise PrFlowError("PR creation succeeded but PR lookup failed.")
    _request_reviewers(pr_ref=str(resolved.number), reviewers=selected_reviewers)
    return resolved


def watch_checks(*, pr: str | None) -> None:
    pr_ref = _resolve_pr_ref(pr)
    _run_or_raise([_resolve_gh_binary(), "pr", "checks", pr_ref, "--watch"])
    print(f"Checks passed for PR {pr_ref}.")


def merge_pr(*, pr: str | None, merge_method: str) -> None:
    pr_ref = _resolve_pr_ref(pr)
    watch_checks(pr=pr_ref)
    method_flag = {
        "merge": "--merge",
        "squash": "--squash",
        "rebase": "--rebase",
    }[merge_method]
    _run_or_raise(
        [
            _resolve_gh_binary(),
            "pr",
            "merge",
            pr_ref,
            method_flag,
            "--delete-branch=false",
        ],
    )
    print(f"Merged PR {pr_ref} with method '{merge_method}'.")


def auto_flow(
    *,
    base: str,
    title: str | None,
    pr: str | None,
    merge_method: str,
    reviewers: list[str] | None,
) -> None:
    if pr is None:
        open_pr(base=base, title=title, reviewers=reviewers)
    merge_pr(pr=pr, merge_method=merge_method)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Automate GitHub PR flow for feature branches.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    open_parser = subparsers.add_parser("open", help="Open PR from current feature branch.")
    open_parser.add_argument("--base", default="develop")
    open_parser.add_argument("--title", default=None)
    open_parser.add_argument(
        "--reviewer",
        action="append",
        default=None,
        help=(
            "GitHub login to request as reviewer. Repeat for multiple reviewers. "
            "Defaults to PR_DEFAULT_REVIEWER or ringxworld."
        ),
    )

    checks_parser = subparsers.add_parser("checks", help="Watch PR checks until completion.")
    checks_parser.add_argument("--pr", default=None)

    merge_parser = subparsers.add_parser("merge", help="Merge PR after checks pass.")
    merge_parser.add_argument("--pr", default=None)
    merge_parser.add_argument(
        "--merge-method",
        default="squash",
        choices=("merge", "squash", "rebase"),
    )

    auto_parser = subparsers.add_parser("auto", help="Open (if needed), wait, and merge PR.")
    auto_parser.add_argument("--base", default="develop")
    auto_parser.add_argument("--title", default=None)
    auto_parser.add_argument("--pr", default=None)
    auto_parser.add_argument(
        "--reviewer",
        action="append",
        default=None,
        help=(
            "GitHub login to request as reviewer. Repeat for multiple reviewers. "
            "Defaults to PR_DEFAULT_REVIEWER or ringxworld."
        ),
    )
    auto_parser.add_argument(
        "--merge-method",
        default="squash",
        choices=("merge", "squash", "rebase"),
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "open":
        open_pr(base=args.base, title=args.title, reviewers=args.reviewer)
        return
    if args.command == "checks":
        watch_checks(pr=args.pr)
        return
    if args.command == "merge":
        merge_pr(pr=args.pr, merge_method=args.merge_method)
        return
    if args.command == "auto":
        auto_flow(
            base=args.base,
            title=args.title,
            pr=args.pr,
            merge_method=args.merge_method,
            reviewers=args.reviewer,
        )
        return
    raise PrFlowError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
