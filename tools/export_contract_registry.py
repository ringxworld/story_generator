"""Export the tracked schema + pipeline contract registry to versioned JSON."""

from __future__ import annotations

import argparse
from pathlib import Path

from story_gen.api.contract_registry import serialize_contract_registry

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "work" / "contracts" / "story_pipeline_contract_registry.v1.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export story contract registry JSON.")
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Output JSON path for contract registry snapshot.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(serialize_contract_registry(indent=2), encoding="utf-8")
    print(f"Wrote contract registry: {output_path}")


if __name__ == "__main__":
    main()
