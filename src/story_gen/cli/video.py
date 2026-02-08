"""CLI runner for video-story ingestion."""

from __future__ import annotations

from story_gen.youtube_downloader import cli_main


def main(argv: list[str] | None = None) -> None:
    cli_main(argv)


if __name__ == "__main__":
    main()
