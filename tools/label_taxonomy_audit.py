"""Audit repository label taxonomy for expected/required governance labels."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

REPO_ROOT = Path(__file__).resolve().parents[1]
WINDOWS_GH_PATH = Path(r"C:\Program Files\GitHub CLI\gh.exe")


@dataclass(frozen=True)
class LabelTaxonomy:
    required_labels: set[str]
    expected_labels: set[str]
    deprecated_aliases: set[str]


@dataclass(frozen=True)
class AuditResult:
    errors: list[str]
    warnings: list[str]
    notes: list[str]


class LabelAuditError(RuntimeError):
    """Raised when audit setup or GH interaction fails."""


def _resolve_gh_binary() -> str:
    if configured := os.environ.get("GH_BIN"):
        candidate = Path(configured)
        if candidate.exists():
            return str(candidate)
        raise LabelAuditError(f"GH_BIN points to missing executable: {candidate}")
    if found := shutil.which("gh"):
        return found
    if os.name == "nt" and WINDOWS_GH_PATH.exists():
        return str(WINDOWS_GH_PATH)
    raise LabelAuditError("GitHub CLI executable not found. Install `gh` or set GH_BIN.")


def _run_gh_labels(*, repo: str) -> list[str]:
    gh_bin = _resolve_gh_binary()
    command = [gh_bin, "label", "list", "--limit", "500", "--json", "name"]
    if repo:
        command.extend(["--repo", repo])
    completed = subprocess.run(
        command,
        check=False,
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "gh label list failed"
        raise LabelAuditError(message)
    payload = cast(list[dict[str, Any]], json.loads(completed.stdout))
    labels = [str(item.get("name", "")).strip() for item in payload if item.get("name")]
    return sorted({label for label in labels if label})


def _load_taxonomy(path: Path) -> LabelTaxonomy:
    if not path.exists():
        raise LabelAuditError(f"Label taxonomy file not found: {path}")
    payload = cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
    required = {str(value).strip() for value in payload.get("required_labels", []) if value}
    expected = {str(value).strip() for value in payload.get("expected_labels", []) if value}
    deprecated = {str(value).strip() for value in payload.get("deprecated_aliases", []) if value}
    if not required:
        raise LabelAuditError("Label taxonomy has no required_labels entries.")
    if not expected:
        raise LabelAuditError("Label taxonomy has no expected_labels entries.")
    return LabelTaxonomy(
        required_labels=required,
        expected_labels=expected,
        deprecated_aliases=deprecated,
    )


def evaluate_label_taxonomy(*, taxonomy: LabelTaxonomy, actual_labels: set[str]) -> AuditResult:
    errors: list[str] = []
    warnings: list[str] = []
    notes: list[str] = []

    missing_required = sorted(taxonomy.required_labels - actual_labels)
    for label in missing_required:
        errors.append(f"Missing required label: {label}")

    missing_expected = sorted(taxonomy.expected_labels - actual_labels)
    for label in missing_expected:
        warnings.append(f"Expected label missing (possible removal): {label}")

    present_deprecated = sorted(taxonomy.deprecated_aliases & actual_labels)
    for label in present_deprecated:
        warnings.append(f"Deprecated/legacy label detected: {label}")

    notes.append(f"actual labels: {len(actual_labels)}")
    notes.append(f"required labels: {len(taxonomy.required_labels)}")
    notes.append(f"expected labels: {len(taxonomy.expected_labels)}")
    notes.append(f"deprecated aliases tracked: {len(taxonomy.deprecated_aliases)}")
    return AuditResult(errors=errors, warnings=warnings, notes=notes)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit GitHub label taxonomy.")
    parser.add_argument(
        "--taxonomy",
        type=Path,
        default=Path(".github/label-taxonomy.json"),
        help="Path to label taxonomy JSON config.",
    )
    parser.add_argument(
        "--repo",
        default="",
        help="Optional owner/repo override (defaults to current gh repo context).",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    return parser


def _print_text(result: AuditResult) -> None:
    print("Label taxonomy audit")
    print("====================")
    for note in result.notes:
        print(f"note: {note}")
    for warning in result.warnings:
        print(f"warning: {warning}")
    for error in result.errors:
        print(f"error: {error}")


def _print_json(result: AuditResult) -> None:
    payload = {
        "errors": result.errors,
        "warnings": result.warnings,
        "notes": result.notes,
    }
    print(json.dumps(payload, indent=2))


def main() -> int:
    args = build_parser().parse_args()
    taxonomy = _load_taxonomy((REPO_ROOT / args.taxonomy).resolve())
    labels = _run_gh_labels(repo=args.repo)
    result = evaluate_label_taxonomy(taxonomy=taxonomy, actual_labels=set(labels))

    if args.format == "json":
        _print_json(result)
    else:
        _print_text(result)
    return 1 if result.errors else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except LabelAuditError as error:
        print(error)
        raise SystemExit(1) from error
