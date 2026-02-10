#!/usr/bin/env python3
"""Export FastAPI OpenAPI schema to a versioned JSON snapshot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from story_gen.api.app import create_app

DEFAULT_OUTPUT = Path("docs/assets/openapi/story_gen.openapi.json")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export story_gen OpenAPI schema snapshot.")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Path to write the OpenAPI JSON snapshot.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if the snapshot on disk does not match generated OpenAPI output.",
    )
    return parser.parse_args()


def _render(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    args = _parse_args()
    output_path = args.output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    app = create_app()
    generated = app.openapi()
    rendered = _render(generated)

    if args.check:
        if not output_path.exists():
            print(f"OpenAPI snapshot missing: {output_path}")
            return 1
        existing = _load_json(output_path)
        if existing != generated:
            print(
                "OpenAPI snapshot drift detected. Run "
                "`uv run python tools/export_openapi_snapshot.py`."
            )
            return 1
        return 0

    output_path.write_text(rendered, encoding="utf-8")
    print(f"Wrote OpenAPI snapshot: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
