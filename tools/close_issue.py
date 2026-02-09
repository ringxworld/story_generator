"""Post a structured close-out summary, then close a GitHub issue."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WINDOWS_GH_PATH = Path(r"C:\Program Files\GitHub CLI\gh.exe")
REQUIRED_SECTIONS = (
    "Work Summary",
    "Objective",
    "Root Cause",
    "Approach",
    "Implementation Details",
    "Validation",
    "Ownership / Follow-ups",
)
PLACEHOLDER_PATTERN = re.compile(r"<[^>\n]{2,}>")


class IssueCloseError(RuntimeError):
    """Raised when issue close workflow cannot proceed safely."""


def _resolve_gh_binary() -> str:
    if configured := os.environ.get("GH_BIN"):
        candidate = Path(configured)
        if candidate.exists():
            return str(candidate)
        raise IssueCloseError(f"GH_BIN points to missing executable: {candidate}")
    if found := shutil.which("gh"):
        return found
    if os.name == "nt" and WINDOWS_GH_PATH.exists():
        return str(WINDOWS_GH_PATH)
    raise IssueCloseError("GitHub CLI executable not found. Install `gh` or set GH_BIN.")


def _run_or_raise(command: list[str]) -> None:
    completed = subprocess.run(
        command,
        check=False,
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip() if completed.stderr else ""
        stdout = completed.stdout.strip() if completed.stdout else ""
        message = stderr or stdout or f"command failed: {' '.join(command)}"
        raise IssueCloseError(message)


def _normalize_section_name(raw: str) -> str:
    return raw.strip().strip(":").strip("*").strip().lower()


def _extract_markdown_sections(text: str) -> set[str]:
    sections: set[str] = set()
    for line in text.splitlines():
        stripped = line.lstrip("\ufeff").strip()
        if not stripped:
            continue

        heading = ""
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip()
        elif stripped.startswith("**") and stripped.endswith("**"):
            heading = stripped.strip("*").strip()
        elif stripped.endswith(":") and len(stripped.split()) <= 6:
            heading = stripped

        if heading:
            sections.add(_normalize_section_name(heading))
    return sections


def validate_summary(summary: str) -> list[str]:
    if not summary.strip():
        return ["Summary file is empty."]

    missing: list[str] = []
    seen_sections = _extract_markdown_sections(summary)
    for required in REQUIRED_SECTIONS:
        if _normalize_section_name(required) not in seen_sections:
            missing.append(required)
    if PLACEHOLDER_PATTERN.search(summary):
        missing.append("Replace placeholder tokens like <component> before closing.")
    return missing


def _load_summary(path: Path) -> str:
    if not path.exists():
        raise IssueCloseError(f"Summary file does not exist: {path}")
    return path.read_text(encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Comment structured close summary and close an issue."
    )
    parser.add_argument("--issue", type=int, required=True, help="Issue number to close.")
    parser.add_argument(
        "--summary-file",
        type=Path,
        required=True,
        help="Markdown file containing required close-out summary sections.",
    )
    parser.add_argument("--repo", default="", help="Optional owner/repo override.")
    parser.add_argument(
        "--reason",
        default="completed",
        choices=("completed", "not planned"),
        help="Close reason passed to GitHub issue close.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate summary without posting comment or closing issue.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    summary = _load_summary(args.summary_file)
    problems = validate_summary(summary)
    if problems:
        detail = "\n- ".join(problems)
        raise IssueCloseError(f"Summary validation failed:\n- {detail}")

    if args.dry_run:
        print(f"Summary for issue #{args.issue} passed validation.")
        return 0

    gh_bin = _resolve_gh_binary()
    repo_args = ["--repo", args.repo] if args.repo else []

    _run_or_raise(
        [
            gh_bin,
            "issue",
            "comment",
            str(args.issue),
            *repo_args,
            "--body-file",
            str(args.summary_file),
        ]
    )
    _run_or_raise(
        [
            gh_bin,
            "issue",
            "close",
            str(args.issue),
            *repo_args,
            "--reason",
            args.reason,
        ]
    )
    print(f"Posted close summary and closed issue #{args.issue}.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except IssueCloseError as error:
        print(error)
        raise SystemExit(1) from error
