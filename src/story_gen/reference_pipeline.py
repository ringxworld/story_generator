"""Reference-story ingestion pipeline for syosetu web novels.

This module supports:
- crawling episode metadata from an index page
- downloading episode text
- optional Japanese->English translation via LibreTranslate
- generating sample output and literary analysis artifacts
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, Mapping, NotRequired, TypedDict
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from bs4.element import Tag

DEFAULT_BASE_URL = "https://ncode.syosetu.com/n2267be/"
DEFAULT_USER_AGENT = "story_gen_reference_bot/0.1 (respectful crawler; personal research use)"
DEFAULT_CRAWL_DELAY_SECONDS = 1.1
DEFAULT_TRANSLATE_DELAY_SECONDS = 0.25
DEFAULT_TRANSLATE_CHUNK_SIZE = 1200


@dataclass(frozen=True)
class EpisodeMeta:
    """Metadata discovered from the table-of-contents pages."""

    episode_number: int
    title_jp: str
    arc_title_jp: str | None
    url: str
    published_at: str | None
    revised_at: str | None


@dataclass(frozen=True)
class EpisodeRecord:
    """Downloaded chapter record with Japanese source text."""

    episode_number: int
    title_jp: str
    arc_title_jp: str | None
    url: str
    published_at: str | None
    revised_at: str | None
    total_episodes_hint: int | None
    text_jp: str


@dataclass(frozen=True)
class PipelineArgs:
    """Typed configuration used by the reference pipeline."""

    base_url: str
    work_dir: str
    project_id: str
    start_page: int
    end_page: int | None
    episode_start: int
    episode_end: int | None
    max_episodes: int | None
    crawl_delay_seconds: float
    force_fetch: bool
    translate_provider: Literal["none", "libretranslate"]
    source_language: str
    target_language: str
    libretranslate_url: str
    libretranslate_api_key: str | None
    translate_delay_seconds: float
    translate_chunk_size: int
    force_translate: bool
    sample_count: int
    excerpt_chars: int
    analysis_names: str


class EpisodeMetaPayload(TypedDict):
    episode_number: int
    title_jp: str
    arc_title_jp: str | None
    url: str
    published_at: str | None
    revised_at: str | None


class EpisodeRecordPayload(TypedDict):
    episode_number: int
    title_jp: str
    arc_title_jp: str | None
    url: str
    published_at: str | None
    revised_at: str | None
    total_episodes_hint: int | None
    text_jp: str


class IndexPayload(TypedDict):
    base_url: str
    fetched_at_utc: str
    total_discovered: int
    selected_count: int
    episodes: list[EpisodeMetaPayload]


class TranslationPayload(TypedDict):
    episode_number: int
    source_language: str
    target_language: str
    text_translated: str


class LongestEpisodePayload(TypedDict):
    episode_number: int
    title_jp: str
    chars: int


class AnalysisPayload(TypedDict):
    episode_count: int
    message: str | None
    total_characters_jp: int
    avg_characters_per_episode_jp: float
    median_characters_per_episode_jp: float
    avg_dialogue_density: float
    max_dialogue_density: float
    episodes_by_arc: dict[str, int]
    focus_name_mentions: dict[str, int]
    top_longest_episodes: list[LongestEpisodePayload]


class LibreTranslateRequest(TypedDict):
    q: str
    source: str
    target: str
    format: str
    api_key: NotRequired[str]


def _episode_meta_payload(meta: EpisodeMeta) -> EpisodeMetaPayload:
    return {
        "episode_number": meta.episode_number,
        "title_jp": meta.title_jp,
        "arc_title_jp": meta.arc_title_jp,
        "url": meta.url,
        "published_at": meta.published_at,
        "revised_at": meta.revised_at,
    }


def _episode_record_payload(record: EpisodeRecord) -> EpisodeRecordPayload:
    return {
        "episode_number": record.episode_number,
        "title_jp": record.title_jp,
        "arc_title_jp": record.arc_title_jp,
        "url": record.url,
        "published_at": record.published_at,
        "revised_at": record.revised_at,
        "total_episodes_hint": record.total_episodes_hint,
        "text_jp": record.text_jp,
    }


def _required_str(mapping: Mapping[str, object], key: str) -> str:
    value = mapping.get(key)
    if isinstance(value, str):
        return value
    raise RuntimeError(f"Invalid or missing string field: {key}")


def _required_int(mapping: Mapping[str, object], key: str) -> int:
    value = mapping.get(key)
    if isinstance(value, bool):
        raise RuntimeError(f"Invalid integer field (bool): {key}")
    if isinstance(value, int):
        return value
    raise RuntimeError(f"Invalid or missing integer field: {key}")


def _optional_str(mapping: Mapping[str, object], key: str) -> str | None:
    value = mapping.get(key)
    if value is None:
        return None
    if isinstance(value, str):
        return value
    raise RuntimeError(f"Invalid optional string field: {key}")


def _optional_int(mapping: Mapping[str, object], key: str) -> int | None:
    value = mapping.get(key)
    if value is None:
        return None
    if isinstance(value, bool):
        raise RuntimeError(f"Invalid optional integer field (bool): {key}")
    if isinstance(value, int):
        return value
    raise RuntimeError(f"Invalid optional integer field: {key}")


def _episode_record_from_loaded(raw: object) -> EpisodeRecord:
    if not isinstance(raw, dict):
        raise RuntimeError("Cached chapter payload is not an object.")
    data: Mapping[str, object] = raw
    payload: EpisodeRecordPayload = {
        "episode_number": _required_int(data, "episode_number"),
        "title_jp": _required_str(data, "title_jp"),
        "arc_title_jp": _optional_str(data, "arc_title_jp"),
        "url": _required_str(data, "url"),
        "published_at": _optional_str(data, "published_at"),
        "revised_at": _optional_str(data, "revised_at"),
        "total_episodes_hint": _optional_int(data, "total_episodes_hint"),
        "text_jp": _required_str(data, "text_jp"),
    }
    return EpisodeRecord(**payload)


def _translated_text_from_loaded(raw: object) -> str | None:
    if not isinstance(raw, dict):
        return None
    data: Mapping[str, object] = raw
    value = data.get("text_translated")
    if isinstance(value, str):
        return value
    return None


def _slug_from_base_url(base_url: str) -> str:
    match = re.search(r"/(n[0-9]+[a-z]+)/?$", base_url)
    if match:
        return match.group(1)
    return "reference_story"


def _parse_revised_timestamp(raw_title: str | None) -> str | None:
    if raw_title is None:
        return None
    match = re.search(r"(\d{4}/\d{2}/\d{2} \d{2}:\d{2})", raw_title)
    if not match:
        return None
    return match.group(1)


def parse_index_page(html: str, base_url: str) -> tuple[list[EpisodeMeta], int]:
    """Parse one syosetu index page into episode metadata."""
    soup = BeautifulSoup(html, "html.parser")

    last_page = 1
    last_link = soup.select_one("a.c-pager__item--last")
    if isinstance(last_link, Tag):
        href = last_link.get("href")
        if isinstance(href, str):
            page_match = re.search(r"[?&]p=(\d+)", href)
            if page_match:
                last_page = int(page_match.group(1))

    episode_list_container = soup.select_one("div.p-eplist")
    if not isinstance(episode_list_container, Tag):
        return ([], last_page)

    current_arc: str | None = None
    episodes: list[EpisodeMeta] = []
    for child in episode_list_container.children:
        if not isinstance(child, Tag):
            continue
        classes = set(child.get("class", []))
        if "p-eplist__chapter-title" in classes:
            current_arc = child.get_text(" ", strip=True) or None
            continue
        if "p-eplist__sublist" not in classes:
            continue

        title_anchor = child.select_one("a.p-eplist__subtitle")
        if not isinstance(title_anchor, Tag):
            continue

        href = title_anchor.get("href")
        if not isinstance(href, str):
            continue
        number_match = re.search(r"/(\d+)/?$", href)
        if not number_match:
            continue

        update_div = child.select_one("div.p-eplist__update")
        published_at: str | None = None
        revised_at: str | None = None
        if isinstance(update_div, Tag):
            update_tokens = list(update_div.stripped_strings)
            if update_tokens:
                published_at = update_tokens[0]
            revised_span = update_div.find("span")
            if isinstance(revised_span, Tag):
                raw_title = revised_span.get("title")
                if isinstance(raw_title, str):
                    revised_at = _parse_revised_timestamp(raw_title)

        episodes.append(
            EpisodeMeta(
                episode_number=int(number_match.group(1)),
                title_jp=title_anchor.get_text(" ", strip=True),
                arc_title_jp=current_arc,
                url=urljoin(base_url, href),
                published_at=published_at,
                revised_at=revised_at,
            )
        )

    return (episodes, last_page)


def parse_episode_page(html: str) -> tuple[str, str, int | None]:
    """Extract chapter title, body text, and total-episodes hint."""
    soup = BeautifulSoup(html, "html.parser")
    title_tag = soup.select_one("h1.p-novel__title")
    title_jp = title_tag.get_text(" ", strip=True) if isinstance(title_tag, Tag) else ""

    total_episodes_hint: int | None = None
    number_tag = soup.select_one("div.p-novel__number")
    if isinstance(number_tag, Tag):
        number_text = number_tag.get_text(" ", strip=True)
        total_match = re.search(r"\d+\s*/\s*(\d+)", number_text)
        if total_match:
            total_episodes_hint = int(total_match.group(1))

    body = soup.select_one("div.js-novel-text.p-novel__text, div.js-novel-text")
    lines: list[str] = []
    if isinstance(body, Tag):
        for paragraph in body.find_all("p"):
            if not isinstance(paragraph, Tag):
                continue
            raw = paragraph.get_text("\n", strip=False).replace("\r\n", "\n")
            normalized = raw.strip("\n")
            if normalized.strip():
                lines.append(normalized)
            else:
                lines.append("")

    compacted: list[str] = []
    last_blank = False
    for line in lines:
        is_blank = not line.strip()
        if is_blank and last_blank:
            continue
        compacted.append(line)
        last_blank = is_blank

    text_jp = "\n".join(compacted).strip()
    return (title_jp, text_jp, total_episodes_hint)


def _chunk_text(text: str, max_chars: int) -> list[str]:
    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    if not paragraphs:
        return [text]

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            if current:
                chunks.append("\n\n".join(current))
                current = []
                current_len = 0
            for i in range(0, len(paragraph), max_chars):
                chunks.append(paragraph[i : i + max_chars])
            continue

        projected = current_len + len(paragraph) + (2 if current else 0)
        if current and projected > max_chars:
            chunks.append("\n\n".join(current))
            current = [paragraph]
            current_len = len(paragraph)
            continue

        current.append(paragraph)
        current_len = projected

    if current:
        chunks.append("\n\n".join(current))
    return chunks


class LibreTranslateTranslator:
    """Translation adapter for LibreTranslate-compatible APIs."""

    def __init__(
        self,
        *,
        client: httpx.Client,
        base_url: str,
        source_language: str = "ja",
        target_language: str = "en",
        api_key: str | None = None,
        delay_seconds: float = DEFAULT_TRANSLATE_DELAY_SECONDS,
        chunk_size: int = DEFAULT_TRANSLATE_CHUNK_SIZE,
    ) -> None:
        self._client = client
        self._endpoint = f"{base_url.rstrip('/')}/translate"
        self._source_language = source_language
        self._target_language = target_language
        self._api_key = api_key
        self._delay_seconds = delay_seconds
        self._chunk_size = chunk_size

    def translate(self, text: str) -> str:
        if not text.strip():
            return ""

        chunks = _chunk_text(text, self._chunk_size)
        translated_chunks: list[str] = []

        for index, chunk in enumerate(chunks):
            payload: LibreTranslateRequest = {
                "q": chunk,
                "source": self._source_language,
                "target": self._target_language,
                "format": "text",
            }
            if self._api_key:
                payload["api_key"] = self._api_key

            response = self._client.post(self._endpoint, json=payload)
            response.raise_for_status()
            raw_data = response.json()
            if not isinstance(raw_data, dict):
                raise RuntimeError("LibreTranslate response was not a JSON object.")
            data: Mapping[str, object] = raw_data
            translated = data.get("translatedText")
            if not isinstance(translated, str):
                raise RuntimeError("LibreTranslate response missing translatedText.")
            translated_chunks.append(translated.strip())

            if index < len(chunks) - 1 and self._delay_seconds > 0:
                time.sleep(self._delay_seconds)

        return "\n\n".join(translated_chunks).strip()


def _load_focus_names(names_argument: str, work_dir: Path) -> list[str]:
    if names_argument.strip():
        return [part.strip() for part in names_argument.split(",") if part.strip()]
    names_file = work_dir / "resources" / "focus_names.txt"
    if names_file.exists():
        raw = names_file.read_text(encoding="utf-8")
        return [line.strip() for line in raw.splitlines() if line.strip()]
    return []


def _dialogue_density(text: str) -> float:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return 0.0
    dialogue_count = 0
    dialogue_openers = ("\u300c", "\u300e", "\u201c", '"', "'")
    for line in lines:
        if line.startswith(dialogue_openers):
            dialogue_count += 1
    return dialogue_count / len(lines)


def build_analysis(episodes: list[EpisodeRecord], focus_names: list[str]) -> AnalysisPayload:
    """Build high-level literary metrics for reference learning."""
    if not episodes:
        return {
            "episode_count": 0,
            "message": "No episodes available for analysis.",
            "total_characters_jp": 0,
            "avg_characters_per_episode_jp": 0.0,
            "median_characters_per_episode_jp": 0.0,
            "avg_dialogue_density": 0.0,
            "max_dialogue_density": 0.0,
            "episodes_by_arc": {},
            "focus_name_mentions": {},
            "top_longest_episodes": [],
        }

    chapter_lengths = [len(episode.text_jp) for episode in episodes]
    dialogue_densities = [_dialogue_density(episode.text_jp) for episode in episodes]

    by_arc: dict[str, int] = {}
    for episode in episodes:
        arc = episode.arc_title_jp or "(no arc label)"
        by_arc[arc] = by_arc.get(arc, 0) + 1

    name_mentions: dict[str, int] = {}
    full_text = "\n".join(episode.text_jp for episode in episodes)
    for name in focus_names:
        name_mentions[name] = full_text.count(name)

    sorted_by_length = sorted(
        episodes,
        key=lambda episode: len(episode.text_jp),
        reverse=True,
    )
    top_longest: list[LongestEpisodePayload] = [
        {
            "episode_number": episode.episode_number,
            "title_jp": episode.title_jp,
            "chars": len(episode.text_jp),
        }
        for episode in sorted_by_length[:10]
    ]

    return {
        "episode_count": len(episodes),
        "message": None,
        "total_characters_jp": sum(chapter_lengths),
        "avg_characters_per_episode_jp": round(statistics.mean(chapter_lengths), 2),
        "median_characters_per_episode_jp": round(statistics.median(chapter_lengths), 2),
        "avg_dialogue_density": round(statistics.mean(dialogue_densities), 4),
        "max_dialogue_density": round(max(dialogue_densities), 4),
        "episodes_by_arc": by_arc,
        "focus_name_mentions": name_mentions,
        "top_longest_episodes": top_longest,
    }


def _analysis_report_markdown(analysis: AnalysisPayload) -> str:
    lines: list[str] = []
    lines.append("# Literary Analysis Report")
    lines.append("")
    lines.append("Generated by `story_gen.reference_pipeline`.")
    lines.append("")
    lines.append(f"- Episode count: {analysis['episode_count']}")
    lines.append(f"- Total JP chars: {analysis['total_characters_jp']}")
    lines.append(f"- Average JP chars/episode: {analysis['avg_characters_per_episode_jp']}")
    lines.append(f"- Median JP chars/episode: {analysis['median_characters_per_episode_jp']}")
    lines.append(f"- Avg dialogue density: {analysis['avg_dialogue_density']}")
    if analysis["message"]:
        lines.append(f"- Note: {analysis['message']}")
    lines.append("")
    lines.append("## Arc Distribution")
    lines.append("")
    for arc, count in sorted(analysis["episodes_by_arc"].items()):
        lines.append(f"- {arc}: {count}")
    lines.append("")
    lines.append("## Focus Name Mentions")
    lines.append("")
    for name, count in sorted(analysis["focus_name_mentions"].items()):
        lines.append(f"- {name}: {count}")
    lines.append("")
    lines.append("## Longest Episodes")
    lines.append("")
    for row in analysis["top_longest_episodes"]:
        lines.append(f"- #{row['episode_number']}: {row['title_jp']} ({row['chars']} chars)")
    lines.append("")
    lines.append("## Reflection Prompts")
    lines.append("")
    lines.append("- Which chapters have the strongest dialogue-to-exposition balance?")
    lines.append("- Where does pacing slow down, and is that intentional or repetitive?")
    lines.append("- Which recurring character interactions create compounding tension?")
    return "\n".join(lines).strip() + "\n"


def _sample_markdown(
    episodes: list[EpisodeRecord],
    translated_map: dict[int, str],
    *,
    sample_count: int,
    excerpt_chars: int,
    base_url: str,
) -> str:
    lines: list[str] = []
    lines.append("# Story Sample (Reference Only)")
    lines.append("")
    lines.append(
        "This sample is generated for private literary analysis. Do not redistribute full text."
    )
    lines.append("")
    lines.append(f"Source: {base_url}")
    lines.append("")

    for episode in episodes[:sample_count]:
        lines.append(f"## Episode {episode.episode_number}: {episode.title_jp}")
        if episode.arc_title_jp:
            lines.append(f"- Arc: {episode.arc_title_jp}")
        lines.append(f"- URL: {episode.url}")
        lines.append("")
        jp_excerpt = episode.text_jp[:excerpt_chars].strip()
        if jp_excerpt:
            lines.append("### Japanese excerpt")
            lines.append("")
            lines.append(jp_excerpt + ("..." if len(episode.text_jp) > len(jp_excerpt) else ""))
            lines.append("")
        en_text = translated_map.get(episode.episode_number)
        if en_text:
            en_excerpt = en_text[:excerpt_chars].strip()
            lines.append("### English excerpt (machine translation)")
            lines.append("")
            lines.append(en_excerpt + ("..." if len(en_text) > len(en_excerpt) else ""))
            lines.append("")

    return "\n".join(lines).strip() + "\n"


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def run_pipeline(args: PipelineArgs) -> None:
    """Execute crawling, optional translation, and analysis export."""
    work_dir = Path(args.work_dir)
    project_slug = args.project_id or _slug_from_base_url(args.base_url)
    output_root = work_dir / "reference_data" / project_slug
    meta_dir = output_root / "meta"
    raw_dir = output_root / "raw"
    translated_dir = output_root / "translated_en"
    samples_dir = output_root / "samples"
    analysis_dir = output_root / "analysis"

    for directory in (meta_dir, raw_dir, translated_dir, samples_dir, analysis_dir):
        directory.mkdir(parents=True, exist_ok=True)

    headers = {"User-Agent": DEFAULT_USER_AGENT}
    with httpx.Client(headers=headers, timeout=60.0, follow_redirects=True) as client:
        start_page = max(1, args.start_page)
        first_url = (
            args.base_url if start_page == 1 else f"{args.base_url.rstrip('/')}/?p={start_page}"
        )
        first_html = client.get(first_url).text
        first_page_episodes, last_page = parse_index_page(first_html, args.base_url)
        target_last_page = min(args.end_page, last_page) if args.end_page is not None else last_page

        all_episode_meta: list[EpisodeMeta] = []
        if start_page <= target_last_page:
            all_episode_meta.extend(first_page_episodes)
            print(
                f"[index] page {start_page}: {len(first_page_episodes)} episodes "
                f"(target pages {start_page}-{target_last_page})"
            )

        for page in range(start_page + 1, target_last_page + 1):
            time.sleep(args.crawl_delay_seconds)
            page_html = client.get(f"{args.base_url.rstrip('/')}/?p={page}").text
            page_episodes, _ = parse_index_page(page_html, args.base_url)
            all_episode_meta.extend(page_episodes)
            print(f"[index] page {page}: {len(page_episodes)} episodes")

        unique_meta: dict[int, EpisodeMeta] = {}
        for item in all_episode_meta:
            unique_meta[item.episode_number] = item

        ordered_meta = [unique_meta[key] for key in sorted(unique_meta.keys())]
        filtered_meta: list[EpisodeMeta] = []
        for meta in ordered_meta:
            if meta.episode_number < args.episode_start:
                continue
            if args.episode_end is not None and meta.episode_number > args.episode_end:
                continue
            filtered_meta.append(meta)
        if args.max_episodes is not None:
            filtered_meta = filtered_meta[: args.max_episodes]

        index_payload: IndexPayload = {
            "base_url": args.base_url,
            "fetched_at_utc": datetime.now(UTC).isoformat(),
            "total_discovered": len(ordered_meta),
            "selected_count": len(filtered_meta),
            "episodes": [_episode_meta_payload(item) for item in filtered_meta],
        }
        _write_json(meta_dir / "index.json", index_payload)

        episode_records: list[EpisodeRecord] = []
        for idx, meta in enumerate(filtered_meta, start=1):
            output_file = raw_dir / f"{meta.episode_number:04d}.json"
            if output_file.exists() and not args.force_fetch:
                raw_cached = json.loads(output_file.read_text(encoding="utf-8"))
                episode_records.append(_episode_record_from_loaded(raw_cached))
                print(f"[raw] {idx}/{len(filtered_meta)} episode {meta.episode_number}: cached")
                continue

            if idx > 1:
                time.sleep(args.crawl_delay_seconds)
            html = client.get(meta.url).text
            title_jp, text_jp, total_hint = parse_episode_page(html)
            record = EpisodeRecord(
                episode_number=meta.episode_number,
                title_jp=title_jp or meta.title_jp,
                arc_title_jp=meta.arc_title_jp,
                url=meta.url,
                published_at=meta.published_at,
                revised_at=meta.revised_at,
                total_episodes_hint=total_hint,
                text_jp=text_jp,
            )
            _write_json(output_file, _episode_record_payload(record))
            episode_records.append(record)
            print(
                f"[raw] {idx}/{len(filtered_meta)} episode {meta.episode_number}: "
                f"saved ({len(text_jp)} chars)"
            )

        translated_map: dict[int, str] = {}
        if args.translate_provider == "libretranslate":
            translator = LibreTranslateTranslator(
                client=client,
                base_url=args.libretranslate_url,
                source_language=args.source_language,
                target_language=args.target_language,
                api_key=args.libretranslate_api_key,
                delay_seconds=args.translate_delay_seconds,
                chunk_size=args.translate_chunk_size,
            )
            print(
                "[translate] using LibreTranslate endpoint "
                f"{args.libretranslate_url} ({args.source_language}->{args.target_language})"
            )
            for idx, episode in enumerate(episode_records, start=1):
                output_file = translated_dir / f"{episode.episode_number:04d}.json"
                if output_file.exists() and not args.force_translate:
                    raw_cached = json.loads(output_file.read_text(encoding="utf-8"))
                    translated_text = _translated_text_from_loaded(raw_cached)
                    if translated_text is not None:
                        translated_map[episode.episode_number] = translated_text
                        print(
                            "[translate] "
                            f"{idx}/{len(episode_records)} episode {episode.episode_number}: cached"
                        )
                        continue

                translated_text = translator.translate(episode.text_jp)
                translated_map[episode.episode_number] = translated_text
                translated_payload: TranslationPayload = {
                    "episode_number": episode.episode_number,
                    "source_language": args.source_language,
                    "target_language": args.target_language,
                    "text_translated": translated_text,
                }
                _write_json(output_file, translated_payload)
                print(
                    "[translate] "
                    f"{idx}/{len(episode_records)} episode {episode.episode_number}: "
                    f"saved ({len(translated_text)} chars)"
                )
        else:
            print("[translate] skipped (provider=none)")

    focus_names = _load_focus_names(args.analysis_names, work_dir)
    analysis = build_analysis(episode_records, focus_names)
    _write_json(analysis_dir / "analysis.json", analysis)
    (analysis_dir / "analysis.md").write_text(
        _analysis_report_markdown(analysis),
        encoding="utf-8",
    )
    (samples_dir / "story_sample.md").write_text(
        _sample_markdown(
            episode_records,
            translated_map,
            sample_count=args.sample_count,
            excerpt_chars=args.excerpt_chars,
            base_url=args.base_url,
        ),
        encoding="utf-8",
    )

    print(f"[done] selected episodes: {len(episode_records)}")
    print(f"[done] output root: {output_root}")


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


def cli_main(argv: list[str] | None = None) -> None:
    """Command-line entrypoint."""
    parser = build_arg_parser()
    parsed = parser.parse_args(argv)
    run_pipeline(_pipeline_args_from_namespace(parsed))
