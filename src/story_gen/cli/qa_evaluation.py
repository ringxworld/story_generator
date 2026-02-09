"""CLI entrypoint for fixture-driven story pipeline QA evaluation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from story_gen.core.pipeline_evaluation import evaluate_fixture_suite, load_fixture_suite

DEFAULT_FIXTURES_PATH = Path("tests/fixtures/story_pipeline_eval_fixtures.v1.json")
DEFAULT_OUTPUT_PATH = Path("work/qa/evaluation_summary.json")


def build_arg_parser() -> argparse.ArgumentParser:
    """Define CLI flags for QA evaluation harness."""
    parser = argparse.ArgumentParser(
        description="Run fixture-driven QA evaluation gates for the story pipeline."
    )
    parser.add_argument("--fixtures", default=str(DEFAULT_FIXTURES_PATH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--strict", action="store_true")
    return parser


def run_evaluation(*, fixtures_path: Path, output_path: Path, strict: bool) -> dict[str, object]:
    """Execute fixture harness and write one JSON summary artifact."""
    suite = load_fixture_suite(fixtures_path)
    summary = evaluate_fixture_suite(suite=suite)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    if strict and summary["status"] != "passed":
        raise SystemExit(1)
    return summary


def main(argv: list[str] | None = None) -> None:
    """CLI entrypoint for QA fixture evaluation."""
    parser = build_arg_parser()
    parsed = parser.parse_args(argv)
    summary = run_evaluation(
        fixtures_path=Path(str(parsed.fixtures)),
        output_path=Path(str(parsed.output)),
        strict=bool(parsed.strict),
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
