"""CLI entrypoint for serving the story_gen HTTP API."""

from __future__ import annotations

import argparse

import uvicorn


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Serve story_gen API.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_arg_parser()
    parsed = parser.parse_args(argv)
    uvicorn.run(
        "story_gen.api.app:app",
        host=str(parsed.host),
        port=int(parsed.port),
        reload=bool(parsed.reload),
    )


if __name__ == "__main__":
    main()
