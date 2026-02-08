"""CLI for reference-story ingestion."""

from __future__ import annotations

import argparse
from typing import Literal

from story_gen.reference_pipeline import (
    DEFAULT_BASE_URL,
    DEFAULT_CRAWL_DELAY_SECONDS,
    DEFAULT_TRANSLATE_CHUNK_SIZE,
    DEFAULT_TRANSLATE_DELAY_SECONDS,
    PipelineArgs,
    run_pipeline,
)


def build_arg_parser() -> argparse.ArgumentParser:
    """CLI definition for the reference ingestion pipeline."""
    parser = argparse.ArgumentParser(
        description="Ingest syosetu chapters for reference-only analysis.",
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--work-dir", default="work")
    parser.add_argument("--project-id", default="")
    parser.add_argument("--start-page", type=int, default=1)
    parser.add_argument("--end-page", type=int, default=0)
    parser.add_argument("--episode-start", type=int, default=1)
    parser.add_argument("--episode-end", type=int, default=0)
    parser.add_argument("--max-episodes", type=int, default=0)
    parser.add_argument("--crawl-delay-seconds", type=float, default=DEFAULT_CRAWL_DELAY_SECONDS)
    parser.add_argument("--force-fetch", action="store_true")
    parser.add_argument("--translate-provider", choices=["none", "libretranslate"], default="none")
    parser.add_argument("--source-language", default="ja")
    parser.add_argument("--target-language", default="en")
    parser.add_argument(
        "--libretranslate-url",
        default="http://localhost:5000",
        help="LibreTranslate base URL, e.g. http://localhost:5000",
    )
    parser.add_argument("--libretranslate-api-key", default="")
    parser.add_argument(
        "--translate-delay-seconds", type=float, default=DEFAULT_TRANSLATE_DELAY_SECONDS
    )
    parser.add_argument("--translate-chunk-size", type=int, default=DEFAULT_TRANSLATE_CHUNK_SIZE)
    parser.add_argument("--force-translate", action="store_true")
    parser.add_argument("--sample-count", type=int, default=5)
    parser.add_argument("--excerpt-chars", type=int, default=800)
    parser.add_argument(
        "--analysis-names",
        default="",
        help="Comma-separated names to count in JP text; "
        "if empty uses work/resources/focus_names.txt when present.",
    )
    return parser


def _pipeline_args_from_namespace(namespace: argparse.Namespace) -> PipelineArgs:
    translate_provider: Literal["none", "libretranslate"]
    if namespace.translate_provider == "libretranslate":
        translate_provider = "libretranslate"
    else:
        translate_provider = "none"

    return PipelineArgs(
        base_url=str(namespace.base_url),
        work_dir=str(namespace.work_dir),
        project_id=str(namespace.project_id),
        start_page=max(1, int(namespace.start_page)),
        end_page=int(namespace.end_page) if int(namespace.end_page) > 0 else None,
        episode_start=max(1, int(namespace.episode_start)),
        episode_end=int(namespace.episode_end) if int(namespace.episode_end) > 0 else None,
        max_episodes=int(namespace.max_episodes) if int(namespace.max_episodes) > 0 else None,
        crawl_delay_seconds=float(namespace.crawl_delay_seconds),
        force_fetch=bool(namespace.force_fetch),
        translate_provider=translate_provider,
        source_language=str(namespace.source_language),
        target_language=str(namespace.target_language),
        libretranslate_url=str(namespace.libretranslate_url),
        libretranslate_api_key=str(namespace.libretranslate_api_key)
        if str(namespace.libretranslate_api_key)
        else None,
        translate_delay_seconds=float(namespace.translate_delay_seconds),
        translate_chunk_size=int(namespace.translate_chunk_size),
        force_translate=bool(namespace.force_translate),
        sample_count=max(1, int(namespace.sample_count)),
        excerpt_chars=max(1, int(namespace.excerpt_chars)),
        analysis_names=str(namespace.analysis_names),
    )


def main(argv: list[str] | None = None) -> None:
    parser = build_arg_parser()
    parsed = parser.parse_args(argv)
    run_pipeline(_pipeline_args_from_namespace(parsed))


if __name__ == "__main__":
    main()
