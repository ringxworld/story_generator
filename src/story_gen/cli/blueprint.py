"""CLI helpers for blueprint JSON workflows."""

from __future__ import annotations

import argparse
from pathlib import Path

from story_gen.api.contracts import load_blueprint_json, save_blueprint_json


def build_arg_parser() -> argparse.ArgumentParser:
    """Define CLI flags for blueprint validation and formatting."""
    parser = argparse.ArgumentParser(description="Validate and normalize story blueprint JSON.")
    parser.add_argument("--input", required=True, help="Path to source blueprint JSON.")
    parser.add_argument(
        "--output",
        default="",
        help="Optional path to write normalized JSON. Defaults to in-place.",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    """Validate blueprint JSON and optionally rewrite in canonical form."""
    parser = build_arg_parser()
    parsed = parser.parse_args(argv)

    input_path = Path(str(parsed.input))
    blueprint = load_blueprint_json(input_path)
    output_path = Path(str(parsed.output)) if str(parsed.output).strip() else input_path
    save_blueprint_json(output_path, blueprint)
    print(f"Validated blueprint: {input_path}")
    if output_path != input_path:
        print(f"Wrote normalized JSON: {output_path}")


if __name__ == "__main__":
    main()
