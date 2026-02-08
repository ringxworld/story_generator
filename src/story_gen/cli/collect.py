"""CLI for story collection."""

from __future__ import annotations

import argparse

from story_gen.story_collector import StoryCollectorArgs, run_story_collection


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collect full chapter text for a Syosetu series.")
    parser.add_argument("--base-url", default="https://ncode.syosetu.com")
    parser.add_argument("--series-code", required=True)
    parser.add_argument("--output-dir", default="work/story_collector")
    parser.add_argument("--output-filename", default="full_story.txt")
    parser.add_argument("--chapter-start", type=int, default=1)
    parser.add_argument("--chapter-end", type=int, default=0)
    parser.add_argument("--max-chapters", type=int, default=0)
    parser.add_argument("--crawl-delay-seconds", type=float, default=1.1)
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument(
        "--user-agent",
        default="story_gen_collector/0.1 (respectful crawler; personal research use)",
    )
    return parser


def _args_from_namespace(namespace: argparse.Namespace) -> StoryCollectorArgs:
    chapter_end_raw = int(namespace.chapter_end)
    max_chapters_raw = int(namespace.max_chapters)
    return StoryCollectorArgs(
        base_url=str(namespace.base_url),
        series_code=str(namespace.series_code).strip("/").lower(),
        output_dir=str(namespace.output_dir),
        output_filename=str(namespace.output_filename),
        chapter_start=max(1, int(namespace.chapter_start)),
        chapter_end=chapter_end_raw if chapter_end_raw > 0 else None,
        max_chapters=max_chapters_raw if max_chapters_raw > 0 else None,
        crawl_delay_seconds=max(0.0, float(namespace.crawl_delay_seconds)),
        max_workers=max(1, int(namespace.max_workers)),
        timeout_seconds=max(1.0, float(namespace.timeout_seconds)),
        user_agent=str(namespace.user_agent),
    )


def main(argv: list[str] | None = None) -> None:
    parser = build_arg_parser()
    parsed = parser.parse_args(argv)
    run_story_collection(_args_from_namespace(parsed))


if __name__ == "__main__":
    main()
