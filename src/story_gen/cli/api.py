"""CLI entrypoint for serving the story_gen HTTP API."""

from __future__ import annotations

import argparse
import os

import uvicorn

from story_gen.adapters.observability import configure_runtime_logging


def build_arg_parser() -> argparse.ArgumentParser:
    """Create CLI args for the local API server process."""
    parser = argparse.ArgumentParser(description="Serve story_gen API.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    parser.add_argument(
        "--db-path",
        default="",
        help="SQLite path for local story persistence (default: work/local/story_gen.db).",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    """Parse CLI flags and start uvicorn with the app factory path."""
    configure_runtime_logging()
    parser = build_arg_parser()
    parsed = parser.parse_args(argv)
    db_path = str(parsed.db_path).strip()
    if db_path:
        os.environ["STORY_GEN_DB_PATH"] = db_path
    uvicorn.run(
        "story_gen.api.app:app",
        host=str(parsed.host),
        port=int(parsed.port),
        reload=bool(parsed.reload),
    )


if __name__ == "__main__":
    main()
