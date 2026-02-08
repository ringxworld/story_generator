"""Collect complete chapter text for a Syosetu series."""

from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict

import httpx

from story_gen.cli.reference_pipeline import parse_episode_page, parse_index_page
from story_gen.pipelines.results import StoryCollectionResult


@dataclass(frozen=True)
class ChapterLink:
    number: int
    title: str
    url: str


@dataclass(frozen=True)
class CollectedChapter:
    number: int
    title: str
    url: str
    body: str


@dataclass(frozen=True)
class StoryCollectorArgs:
    base_url: str
    series_code: str
    output_dir: str
    output_filename: str
    chapter_start: int
    chapter_end: int | None
    max_chapters: int | None
    crawl_delay_seconds: float
    max_workers: int
    timeout_seconds: float
    user_agent: str


class ChapterMetaPayload(TypedDict):
    number: int
    title: str
    url: str
    chars: int


class CollectionPayload(TypedDict):
    base_url: str
    series_code: str
    fetched_at_utc: str
    chapter_count: int
    output_file: str
    chapters: list[ChapterMetaPayload]


def _series_root(base_url: str, series_code: str) -> str:
    return f"{base_url.rstrip('/')}/{series_code.strip('/').lower()}/"


def _index_page_url(base_url: str, series_code: str, page: int) -> str:
    root = _series_root(base_url, series_code)
    if page <= 1:
        return root
    return f"{root}?p={page}"


def _fetch_text(client: httpx.Client, url: str) -> str:
    return client.get(url).text


def collect_chapter_links(args: StoryCollectorArgs) -> list[ChapterLink]:
    headers = {"User-Agent": args.user_agent}
    with httpx.Client(
        headers=headers, timeout=args.timeout_seconds, follow_redirects=True
    ) as client:
        first_page_url = _index_page_url(args.base_url, args.series_code, 1)
        first_html = _fetch_text(client, first_page_url)
        first_page_episodes, last_page = parse_index_page(first_html, first_page_url)

        all_links: dict[int, ChapterLink] = {}
        for episode in first_page_episodes:
            all_links[episode.episode_number] = ChapterLink(
                number=episode.episode_number,
                title=episode.title_jp,
                url=episode.url,
            )

        for page in range(2, last_page + 1):
            time.sleep(args.crawl_delay_seconds)
            page_url = _index_page_url(args.base_url, args.series_code, page)
            page_html = _fetch_text(client, page_url)
            page_episodes, _ = parse_index_page(page_html, page_url)
            for episode in page_episodes:
                all_links[episode.episode_number] = ChapterLink(
                    number=episode.episode_number,
                    title=episode.title_jp,
                    url=episode.url,
                )

    ordered = [all_links[number] for number in sorted(all_links)]
    filtered: list[ChapterLink] = []
    for link in ordered:
        if link.number < args.chapter_start:
            continue
        if args.chapter_end is not None and link.number > args.chapter_end:
            continue
        filtered.append(link)
    if args.max_chapters is not None:
        filtered = filtered[: args.max_chapters]
    return filtered


def _fetch_chapter_once(link: ChapterLink, args: StoryCollectorArgs) -> CollectedChapter:
    headers = {"User-Agent": args.user_agent}
    with httpx.Client(
        headers=headers, timeout=args.timeout_seconds, follow_redirects=True
    ) as client:
        html = _fetch_text(client, link.url)
    return _chapter_from_html(link, html)


def _chapter_from_html(link: ChapterLink, html: str) -> CollectedChapter:
    title_page, body, _ = parse_episode_page(html)
    effective_title = title_page or link.title or f"Chapter {link.number}"
    return CollectedChapter(number=link.number, title=effective_title, url=link.url, body=body)


def collect_chapters(args: StoryCollectorArgs, links: list[ChapterLink]) -> list[CollectedChapter]:
    if args.max_workers <= 1:
        headers = {"User-Agent": args.user_agent}
        chapters: list[CollectedChapter] = []
        with httpx.Client(
            headers=headers,
            timeout=args.timeout_seconds,
            follow_redirects=True,
        ) as client:
            for index, link in enumerate(links):
                if index > 0:
                    time.sleep(args.crawl_delay_seconds)
                html = _fetch_text(client, link.url)
                chapters.append(_chapter_from_html(link, html))
        return chapters

    by_number: dict[int, CollectedChapter] = {}
    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        future_map = {
            executor.submit(_fetch_chapter_once, link, args): link.number for link in links
        }
        for future in as_completed(future_map):
            chapter = future.result()
            by_number[chapter.number] = chapter
    return [by_number[number] for number in sorted(by_number)]


def _write_collection_outputs(
    output_root: Path,
    output_filename: str,
    base_url: str,
    series_code: str,
    chapters: list[CollectedChapter],
) -> StoryCollectionResult:
    output_root.mkdir(parents=True, exist_ok=True)
    chapters_dir = output_root / "chapters"
    chapters_dir.mkdir(parents=True, exist_ok=True)

    full_story_path = output_root / output_filename
    with full_story_path.open("w", encoding="utf-8") as handle:
        for chapter in chapters:
            handle.write(f"===== Chapter {chapter.number}: {chapter.title} =====\n\n")
            handle.write(chapter.body)
            handle.write("\n\n\n")

    for chapter in chapters:
        chapter_file = chapters_dir / f"{chapter.number:04d}.txt"
        chapter_file.write_text(chapter.body, encoding="utf-8")

    payload: CollectionPayload = {
        "base_url": base_url,
        "series_code": series_code,
        "fetched_at_utc": datetime.now(UTC).isoformat(),
        "chapter_count": len(chapters),
        "output_file": str(full_story_path),
        "chapters": [
            {
                "number": chapter.number,
                "title": chapter.title,
                "url": chapter.url,
                "chars": len(chapter.body),
            }
            for chapter in chapters
        ],
    }
    index_path = output_root / "index.json"
    index_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return StoryCollectionResult(
        output_root=output_root,
        full_story_path=full_story_path,
        index_path=index_path,
        chapter_count=len(chapters),
    )


def run_story_collection(args: StoryCollectorArgs) -> StoryCollectionResult:
    links = collect_chapter_links(args)
    print(f"[collect] discovered chapters: {len(links)}")
    chapters = collect_chapters(args, links)
    output_root = Path(args.output_dir) / args.series_code
    result = _write_collection_outputs(
        output_root=output_root,
        output_filename=args.output_filename,
        base_url=args.base_url,
        series_code=args.series_code,
        chapters=chapters,
    )
    print(f"[collect] wrote output to: {result.output_root}")
    return result


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
