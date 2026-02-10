"""Maintain a running total of prevented bugs based on test coverage."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_JSON_PATH = Path("docs/assets/bug_prevention.json")
DEFAULT_MD_PATH = Path("docs/bug_prevention.md")


@dataclass(frozen=True)
class BugPreventionEntry:
    entry_id: str
    title: str
    tests: list[str]
    issue_url: str | None
    prevented_count: int
    notes: str | None
    logged_at_utc: str


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"total_prevented": 0, "entries": []}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("Bug prevention log JSON must be an object.")
    payload.setdefault("entries", [])
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _render_markdown(total: int, entries: list[BugPreventionEntry]) -> str:
    lines: list[str] = []
    lines.append("# Bug Prevention Log")
    lines.append("")
    lines.append("This log tracks issues prevented by test coverage. It is generated from")
    lines.append("`docs/assets/bug_prevention.json`.")
    lines.append("")
    lines.append("## Total Prevented")
    lines.append("")
    lines.append(f"Total prevented: {total}")
    lines.append("")
    lines.append("## Entries")
    lines.append("")
    lines.append("| Logged At (UTC) | Prevented | Title | Tests | Issue |")
    lines.append("| --- | --- | --- | --- | --- |")
    for entry in entries:
        tests = ", ".join(entry.tests) if entry.tests else "-"
        issue = entry.issue_url or "-"
        lines.append(
            f"| {entry.logged_at_utc} | {entry.prevented_count} | {entry.title} | {tests} | {issue} |"
        )
    lines.append("")
    return "\n".join(lines)


def _entry_from_args(args: argparse.Namespace) -> BugPreventionEntry:
    logged_at = datetime.now(UTC).isoformat()
    entry_id = args.entry_id or f"log-{logged_at.replace(':', '').replace('-', '')}"
    tests = [item.strip() for item in args.tests.split(",") if item.strip()]
    issue_url = args.issue_url.strip() if args.issue_url else None
    notes = args.notes.strip() if args.notes else None
    return BugPreventionEntry(
        entry_id=entry_id,
        title=args.title.strip(),
        tests=tests,
        issue_url=issue_url,
        prevented_count=max(1, int(args.prevented_count)),
        notes=notes,
        logged_at_utc=logged_at,
    )


def log_prevention(args: argparse.Namespace) -> None:
    json_path = Path(args.json_path)
    md_path = Path(args.md_path)
    payload = _load_json(json_path)
    raw_entries = payload.get("entries", [])
    if not isinstance(raw_entries, list):
        raise RuntimeError("Bug prevention log entries must be a list.")

    entry = _entry_from_args(args)
    raw_entries.append(
        {
            "entry_id": entry.entry_id,
            "title": entry.title,
            "tests": entry.tests,
            "issue_url": entry.issue_url,
            "prevented_count": entry.prevented_count,
            "notes": entry.notes,
            "logged_at_utc": entry.logged_at_utc,
        }
    )

    entries: list[BugPreventionEntry] = []
    for raw in raw_entries:
        if not isinstance(raw, dict):
            continue
        entries.append(
            BugPreventionEntry(
                entry_id=str(raw.get("entry_id", "")).strip(),
                title=str(raw.get("title", "")).strip(),
                tests=[str(item) for item in raw.get("tests", []) if str(item).strip()],
                issue_url=str(raw.get("issue_url", "")).strip() or None,
                prevented_count=int(raw.get("prevented_count", 0)),
                notes=str(raw.get("notes", "")).strip() or None,
                logged_at_utc=str(raw.get("logged_at_utc", "")).strip(),
            )
        )

    total = sum(entry.prevented_count for entry in entries if entry.prevented_count > 0)
    payload = {
        "total_prevented": total,
        "entries": [
            {
                "entry_id": entry.entry_id,
                "title": entry.title,
                "tests": entry.tests,
                "issue_url": entry.issue_url,
                "prevented_count": entry.prevented_count,
                "notes": entry.notes,
                "logged_at_utc": entry.logged_at_utc,
            }
            for entry in entries
        ],
    }
    _write_json(json_path, payload)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_render_markdown(total, entries), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Log a prevented bug entry.")
    parser.add_argument("--title", required=True, help="Short title for the prevented bug.")
    parser.add_argument(
        "--tests",
        default="",
        help="Comma-separated list of tests that prevented the bug.",
    )
    parser.add_argument("--issue-url", default="", help="Related issue URL (optional).")
    parser.add_argument("--notes", default="", help="Additional notes (optional).")
    parser.add_argument("--prevented-count", type=int, default=1)
    parser.add_argument("--entry-id", default="")
    parser.add_argument("--json-path", default=str(DEFAULT_JSON_PATH))
    parser.add_argument("--md-path", default=str(DEFAULT_MD_PATH))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    log_prevention(args)


if __name__ == "__main__":
    main()
