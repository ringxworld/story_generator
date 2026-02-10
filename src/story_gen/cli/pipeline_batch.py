"""Batch pipeline runner for chapter directories."""

from __future__ import annotations

import argparse
import json
import re
import statistics
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

import httpx

from story_gen.core.story_analysis_pipeline import run_story_analysis
from story_gen.core.story_schema import StoryDocument


@dataclass(frozen=True)
class ChapterSummary:
    chapter_number: int
    source_path: str
    translated: bool
    translation_provider: str
    source_language: str
    source_chars: int
    translated_chars: int
    event_count: int
    beat_count: int
    theme_count: int
    insight_count: int
    top_entities: list[str]
    top_themes: list[str]
    quality_passed: bool
    translation_quality: float
    timing_seconds: dict[str, float]


@dataclass(frozen=True)
class BatchSummary:
    run_id: str
    started_at_utc: str
    finished_at_utc: str
    total_chapters: int
    processed_chapters: int
    skipped_chapters: int
    failed_chapters: int
    failures: list[dict[str, object]]
    elapsed_seconds: float
    average_chapter_seconds: float
    translation_provider: str
    timing_totals: dict[str, float]


class TranslationError(RuntimeError):
    """Raised when translation fails for a chapter."""


class Translator(Protocol):
    name: str

    def translate(self, text: str) -> str: ...


class ArgosTranslator:
    name = "argos.v1"

    def __init__(self, source_language: str, target_language: str) -> None:
        try:
            import argostranslate.translate as argos_translate  # type: ignore
        except Exception as exc:  # noqa: BLE001
            raise TranslationError("argostranslate is not installed") from exc
        languages = argos_translate.get_installed_languages()
        source = next((lang for lang in languages if lang.code == source_language), None)
        target = next((lang for lang in languages if lang.code == target_language), None)
        if source is None or target is None:
            raise TranslationError(
                f"argostranslate missing language pair {source_language}->{target_language}"
            )
        self._translator = source.get_translation(target)

    def translate(self, text: str) -> str:
        return str(self._translator.translate(text))


class LibreTranslateClient:
    name = "libretranslate.v1"

    def __init__(
        self,
        *,
        base_url: str,
        source_language: str,
        target_language: str,
        api_key: str | None,
        delay_seconds: float,
        chunk_size: int,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._source_language = source_language
        self._target_language = target_language
        self._api_key = api_key
        self._delay_seconds = delay_seconds
        self._chunk_size = chunk_size

    def translate(self, text: str) -> str:
        if not text.strip():
            return ""
        chunks = _chunk_text(text, self._chunk_size)
        translated: list[str] = []
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            for index, chunk in enumerate(chunks, start=1):
                translated.append(
                    _translate_with_retry(
                        client=client,
                        base_url=self._base_url,
                        text=chunk,
                        source_language=self._source_language,
                        target_language=self._target_language,
                        api_key=self._api_key,
                    )
                )
                if index < len(chunks) and self._delay_seconds > 0:
                    time.sleep(self._delay_seconds)
        return "\n\n".join(translated).strip()


_STAGE_ORDER = ("setup", "escalation", "climax", "resolution")
_STOPWORD_ENTITIES = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "be",
    "but",
    "by",
    "for",
    "from",
    "he",
    "her",
    "his",
    "i",
    "if",
    "in",
    "is",
    "it",
    "its",
    "me",
    "my",
    "of",
    "on",
    "or",
    "she",
    "so",
    "that",
    "the",
    "their",
    "them",
    "there",
    "they",
    "this",
    "to",
    "was",
    "we",
    "were",
    "with",
    "you",
}


def _translate_with_retry(
    *,
    client: httpx.Client,
    base_url: str,
    text: str,
    source_language: str,
    target_language: str,
    api_key: str | None,
) -> str:
    last_error: Exception | None = None
    for attempt in range(1, 6):
        try:
            payload: dict[str, object] = {
                "q": text,
                "source": source_language,
                "target": target_language,
                "format": "text",
            }
            if api_key:
                payload["api_key"] = api_key
            response = client.post(f"{base_url}/translate", json=payload)
            if response.status_code in {429, 503}:
                raise TranslationError(f"LibreTranslate throttled: {response.status_code}")
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                raise TranslationError("LibreTranslate response was not an object")
            translated = data.get("translatedText")
            if not isinstance(translated, str) or not translated.strip():
                raise TranslationError("LibreTranslate response missing translatedText")
            return translated.strip()
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(min(8.0, 0.6 * attempt))
    if last_error is not None:
        raise TranslationError(str(last_error)) from last_error
    raise TranslationError("LibreTranslate failed without error detail")


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


def _looks_untranslated(source: str, translated: str) -> bool:
    if not translated.strip():
        return True
    source_has_jp = sum(
        1 for ch in source if "\u3040" <= ch <= "\u30ff" or "\u4e00" <= ch <= "\u9fff"
    )
    if source_has_jp == 0:
        return False
    translated_ascii = sum(1 for ch in translated if "a" <= ch.lower() <= "z")
    unknown_ratio = translated.count("?") / max(1, len(translated))
    return translated_ascii < 10 or unknown_ratio > 0.2


def _translator_chain(
    *,
    provider: str,
    source_language: str,
    target_language: str,
    libretranslate_url: str,
    libretranslate_api_key: str | None,
    translate_delay_seconds: float,
    translate_chunk_size: int,
) -> list[Translator]:
    if provider == "none":
        return []
    chain: list[Translator] = []
    if provider in {"argos", "chain"}:
        try:
            chain.append(ArgosTranslator(source_language, target_language))
        except TranslationError:
            if provider == "argos":
                raise
    if provider in {"libretranslate", "chain"}:
        chain.append(
            LibreTranslateClient(
                base_url=libretranslate_url,
                source_language=source_language,
                target_language=target_language,
                api_key=libretranslate_api_key,
                delay_seconds=translate_delay_seconds,
                chunk_size=translate_chunk_size,
            )
        )
    return chain


def _translate_text(
    *,
    source_text: str,
    chain: list[Translator],
) -> tuple[str, str]:
    if not chain:
        return source_text, "none"
    last_error: Exception | None = None
    for translator in chain:
        name = getattr(translator, "name", "unknown")
        try:
            translated = translator.translate(source_text)
            if _looks_untranslated(source_text, translated):
                raise TranslationError(f"{name} produced low-quality output")
            return translated, name
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            continue
    if last_error is not None:
        raise TranslationError(str(last_error)) from last_error
    raise TranslationError("translation failed")


def _chapter_number(path: Path) -> int:
    stem = path.stem
    try:
        return int(stem)
    except ValueError:
        return 0


def _summarize_document(document: StoryDocument) -> tuple[list[str], list[str]]:
    entities = sorted(document.entity_mentions, key=lambda ent: (-ent.mention_count, ent.name))
    themes = sorted(document.theme_signals, key=lambda theme: (-theme.strength, theme.label))
    top_entities = [entity.name for entity in entities[:6]]
    top_themes = [theme.label for theme in themes[:6]]
    return top_entities, top_themes


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _parse_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _parse_float_mapping(value: object) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}
    parsed: dict[str, float] = {}
    for key, raw in value.items():
        if not isinstance(key, str):
            continue
        if isinstance(raw, (int, float)):
            parsed[key] = float(raw)
    return parsed


def _chapter_summary_from_payload(payload: object) -> ChapterSummary | None:
    if not isinstance(payload, dict):
        return None
    chapter_number = payload.get("chapter_number")
    source_path = payload.get("source_path")
    translated = payload.get("translated")
    translation_provider = payload.get("translation_provider")
    source_language = payload.get("source_language")
    source_chars = payload.get("source_chars")
    translated_chars = payload.get("translated_chars")
    event_count = payload.get("event_count")
    beat_count = payload.get("beat_count")
    theme_count = payload.get("theme_count")
    insight_count = payload.get("insight_count")
    quality_passed = payload.get("quality_passed")
    translation_quality = payload.get("translation_quality")

    if not isinstance(chapter_number, int):
        return None
    if not isinstance(source_path, str):
        return None
    if not isinstance(translated, bool):
        return None
    if not isinstance(translation_provider, str):
        return None
    if not isinstance(source_language, str):
        return None
    if not isinstance(source_chars, int):
        return None
    if not isinstance(translated_chars, int):
        return None
    if not isinstance(event_count, int):
        return None
    if not isinstance(beat_count, int):
        return None
    if not isinstance(theme_count, int):
        return None
    if not isinstance(insight_count, int):
        return None
    if not isinstance(quality_passed, bool):
        return None
    if not isinstance(translation_quality, (int, float)):
        return None

    return ChapterSummary(
        chapter_number=chapter_number,
        source_path=source_path,
        translated=translated,
        translation_provider=translation_provider,
        source_language=source_language,
        source_chars=source_chars,
        translated_chars=translated_chars,
        event_count=event_count,
        beat_count=beat_count,
        theme_count=theme_count,
        insight_count=insight_count,
        top_entities=_parse_string_list(payload.get("top_entities")),
        top_themes=_parse_string_list(payload.get("top_themes")),
        quality_passed=quality_passed,
        translation_quality=float(translation_quality),
        timing_seconds=_parse_float_mapping(payload.get("timing_seconds")),
    )


def _clean_entity(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9 '\-]", "", value.strip().lower()).strip()
    if len(normalized) < 3:
        return ""
    if normalized in _STOPWORD_ENTITIES:
        return ""
    if normalized.isdigit():
        return ""
    return normalized


def _chapter_stage(index: int, total: int) -> str:
    if total <= 1:
        return "setup"
    ratio = (index + 1) / float(total)
    if ratio <= 0.25:
        return "setup"
    if ratio <= 0.6:
        return "escalation"
    if ratio <= 0.85:
        return "climax"
    return "resolution"


def _dashboard_payload(
    *,
    run_summary: BatchSummary,
    chapter_summaries: list[ChapterSummary],
) -> dict[str, object]:
    sorted_chapters = sorted(chapter_summaries, key=lambda item: item.chapter_number)
    chapter_count = len(sorted_chapters)
    chapter_chars = [item.source_chars for item in sorted_chapters]
    total_chars = sum(chapter_chars)
    median_chars = int(statistics.median(chapter_chars)) if chapter_chars else 0
    over_10k = sum(1 for chars in chapter_chars if chars >= 10_000)
    event_total = sum(item.event_count for item in sorted_chapters)
    beat_total = sum(item.beat_count for item in sorted_chapters)
    theme_total = sum(item.theme_count for item in sorted_chapters)
    insight_total = sum(item.insight_count for item in sorted_chapters)
    pass_count = sum(1 for item in sorted_chapters if item.quality_passed)
    quality_pass_rate = (pass_count / chapter_count) if chapter_count else 0.0
    average_translation_quality = (
        sum(item.translation_quality for item in sorted_chapters) / chapter_count
        if chapter_count
        else 0.0
    )

    theme_scores: dict[str, float] = {}
    theme_stage_scores: dict[tuple[str, str], float] = {}
    stage_buckets: dict[str, dict[str, list[float]]] = {
        stage: {"events_per_1k_chars": [], "themes_per_1k_chars": [], "translation_quality": []}
        for stage in _STAGE_ORDER
    }
    timeline_story_items: list[dict[str, object]] = []
    timeline_quality_items: list[dict[str, object]] = []
    chapter_theme_map: dict[int, list[str]] = {}
    chapter_entity_map: dict[int, list[str]] = {}

    for index, chapter in enumerate(sorted_chapters):
        stage = _chapter_stage(index, chapter_count)
        top_themes = [theme for theme in chapter.top_themes if theme.strip()]
        top_theme_labels = ", ".join(top_themes[:2]) if top_themes else "no dominant theme"
        timeline_story_items.append(
            {
                "id": f"chapter-{chapter.chapter_number:04d}",
                "label": f"Chapter {chapter.chapter_number:04d}: {top_theme_labels}",
                "order": index + 1,
                "time": None,
            }
        )
        quality_label = "pass" if chapter.quality_passed else "fail"
        timeline_quality_items.append(
            {
                "id": f"quality-{chapter.chapter_number:04d}",
                "label": (
                    f"Chapter {chapter.chapter_number:04d}: {quality_label}, "
                    f"tq={chapter.translation_quality:.2f}, events={chapter.event_count}"
                ),
                "order": index + 1,
                "time": None,
            }
        )

        chapter_theme_map[chapter.chapter_number] = top_themes
        cleaned_entities = [_clean_entity(entity) for entity in chapter.top_entities]
        chapter_entity_map[chapter.chapter_number] = [
            entity for entity in cleaned_entities if entity
        ]

        char_scale = max(1, chapter.source_chars)
        stage_buckets[stage]["events_per_1k_chars"].append(
            chapter.event_count * 1000.0 / char_scale
        )
        stage_buckets[stage]["themes_per_1k_chars"].append(
            chapter.theme_count * 1000.0 / char_scale
        )
        stage_buckets[stage]["translation_quality"].append(chapter.translation_quality)

        for rank, theme in enumerate(top_themes[:4]):
            score = 1.0 / float(rank + 1)
            theme_scores[theme] = theme_scores.get(theme, 0.0) + score
            key = (theme, stage)
            theme_stage_scores[key] = theme_stage_scores.get(key, 0.0) + score

    max_theme_stage_score = max(theme_stage_scores.values(), default=0.0)
    heatmap = [
        {
            "theme": theme,
            "stage": stage,
            "intensity": round(
                (score / max_theme_stage_score) if max_theme_stage_score > 0 else 0.0, 2
            ),
        }
        for (theme, stage), score in sorted(
            theme_stage_scores.items(),
            key=lambda item: (-item[1], item[0][0], item[0][1]),
        )[:24]
    ]

    arc_points: list[dict[str, object]] = []
    for lane in ("events_per_1k_chars", "themes_per_1k_chars", "translation_quality"):
        for stage in _STAGE_ORDER:
            values = stage_buckets[stage][lane]
            if not values:
                continue
            average_value = sum(values) / len(values)
            arc_points.append(
                {
                    "lane": lane,
                    "stage": stage,
                    "value": round(average_value, 3),
                    "label": f"{average_value:.3f}",
                }
            )

    top_themes = [
        theme for theme, _ in sorted(theme_scores.items(), key=lambda item: (-item[1], item[0]))[:8]
    ]
    chapter_nodes = sorted_chapters[:16]
    graph_nodes: list[dict[str, object]] = []
    graph_edges: list[dict[str, object]] = []

    for index, theme in enumerate(top_themes):
        graph_nodes.append(
            {
                "id": f"theme:{theme}",
                "label": theme,
                "group": "theme",
                "stage": None,
                "layout_x": 60 + index * 64,
                "layout_y": 40,
            }
        )

    for index, chapter in enumerate(chapter_nodes):
        x_slot = index % 8
        y_slot = index // 8
        chapter_node_id = f"chapter:{chapter.chapter_number:04d}"
        graph_nodes.append(
            {
                "id": chapter_node_id,
                "label": f"C{chapter.chapter_number:04d}",
                "group": "chapter",
                "stage": _chapter_stage(index, len(chapter_nodes)),
                "layout_x": 60 + x_slot * 64,
                "layout_y": 122 + y_slot * 70,
            }
        )
        for rank, theme in enumerate(chapter_theme_map.get(chapter.chapter_number, [])[:2]):
            if theme not in top_themes:
                continue
            graph_edges.append(
                {
                    "source": chapter_node_id,
                    "target": f"theme:{theme}",
                    "relation": "mentions_theme",
                    "weight": round(1.0 / float(rank + 1), 3),
                }
            )
        for entity in chapter_entity_map.get(chapter.chapter_number, [])[:1]:
            entity_node_id = f"entity:{entity}"
            if all(node["id"] != entity_node_id for node in graph_nodes):
                graph_nodes.append(
                    {
                        "id": entity_node_id,
                        "label": entity[:18],
                        "group": "entity",
                        "stage": None,
                        "layout_x": 420 + (len(graph_nodes) % 3) * 52,
                        "layout_y": 40 + (len(graph_nodes) % 4) * 42,
                    }
                )
            graph_edges.append(
                {
                    "source": chapter_node_id,
                    "target": entity_node_id,
                    "relation": "mentions_entity",
                    "weight": 0.4,
                }
            )

    dominant_theme = top_themes[0] if top_themes else "story"
    macro_thesis = (
        f"Across {chapter_count} chapters, the strongest recurring signal is '{dominant_theme}' "
        f"with {event_total} extracted events and {insight_total} generated insights."
    )

    return {
        "run": {
            "run_id": run_summary.run_id,
            "started_at_utc": run_summary.started_at_utc,
            "finished_at_utc": run_summary.finished_at_utc,
            "elapsed_seconds": run_summary.elapsed_seconds,
            "average_chapter_seconds": run_summary.average_chapter_seconds,
            "translation_provider": run_summary.translation_provider,
            "timing_totals": run_summary.timing_totals,
        },
        "overview": {
            "title": "Re:Zero End-to-End Batch Dashboard",
            "macro_thesis": macro_thesis,
            "confidence_floor": round(average_translation_quality, 3),
            "quality_passed": run_summary.failed_chapters == 0 and quality_pass_rate >= 0.5,
            "events_count": event_total,
            "beats_count": beat_total,
            "themes_count": theme_total,
            "insights_count": insight_total,
        },
        "kpis": {
            "chapter_count": chapter_count,
            "chapter_chars_total": total_chars,
            "chapter_chars_median": median_chars,
            "chapters_over_10000_chars": over_10k,
            "quality_pass_rate": round(quality_pass_rate, 3),
            "average_translation_quality": round(average_translation_quality, 3),
            "failed_chapters": run_summary.failed_chapters,
        },
        "timeline": [
            {"lane": "chapter_order", "items": timeline_story_items},
            {"lane": "quality_gate", "items": timeline_quality_items},
        ],
        "heatmap": heatmap,
        "arcs": arc_points,
        "graph": {
            "nodes": graph_nodes,
            "edges": graph_edges,
        },
    }


def run_pipeline_batch(args: argparse.Namespace) -> BatchSummary:
    source_dir = Path(args.source_dir)
    output_root = Path(args.output_dir) / args.run_id
    output_root.mkdir(parents=True, exist_ok=True)
    summaries_dir = output_root / "chapters"
    summaries_dir.mkdir(parents=True, exist_ok=True)
    translated_dir = (
        Path(args.translated_dir) if args.translated_dir else output_root / "translated_en"
    )
    translated_dir.mkdir(parents=True, exist_ok=True)

    chain = _translator_chain(
        provider=args.translate_provider,
        source_language=args.source_language,
        target_language=args.target_language,
        libretranslate_url=args.libretranslate_url,
        libretranslate_api_key=args.libretranslate_api_key or None,
        translate_delay_seconds=args.translate_delay_seconds,
        translate_chunk_size=args.translate_chunk_size,
    )

    files = sorted(source_dir.glob("*.txt"), key=_chapter_number)
    filtered: list[Path] = []
    for path in files:
        number = _chapter_number(path)
        if number < args.chapter_start:
            continue
        if args.chapter_end and number > args.chapter_end:
            continue
        filtered.append(path)
    if args.max_chapters:
        filtered = filtered[: args.max_chapters]

    started = time.perf_counter()
    started_at = datetime.now(UTC).isoformat()
    processed = 0
    skipped = 0
    failed = 0
    failures: list[dict[str, object]] = []
    timing_totals: dict[str, float] = {}
    chapter_summaries: list[ChapterSummary] = []

    for path in filtered:
        number = _chapter_number(path)
        summary_path = summaries_dir / f"{number:04d}.json"
        if summary_path.exists() and not args.force:
            existing_summary = _chapter_summary_from_payload(
                json.loads(summary_path.read_text(encoding="utf-8"))
            )
            if existing_summary is not None:
                chapter_summaries.append(existing_summary)
            skipped += 1
            continue

        try:
            raw_text = path.read_text(encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            failures.append({"chapter_number": number, "stage": "read", "error": str(exc)})
            if args.strict:
                raise
            continue

        translated_text = raw_text
        translated = False
        provider_used = "none"
        if args.mode in {"translate", "all"} and args.translate_provider != "none":
            try:
                translated_text, provider_used = _translate_text(source_text=raw_text, chain=chain)
                translated = provider_used != "none"
                translated_path = translated_dir / path.name
                translated_path.write_text(translated_text + "\n", encoding="utf-8")
            except Exception as exc:  # noqa: BLE001
                failed += 1
                failures.append({"chapter_number": number, "stage": "translate", "error": str(exc)})
                if args.strict:
                    raise
                continue
        elif args.mode in {"analyze", "all"} and translated_dir.exists():
            translated_path = translated_dir / path.name
            if translated_path.exists():
                translated_text = translated_path.read_text(encoding="utf-8")
                translated = True

        if args.mode in {"translate"}:
            processed += 1
            continue

        try:
            analysis = run_story_analysis(
                story_id=f"{args.story_id_prefix}{number:04d}",
                source_text=translated_text,
                source_type="text",
                target_language=args.target_language,
            )
            top_entities, top_themes = _summarize_document(analysis.document)
            chapter_summary = ChapterSummary(
                chapter_number=number,
                source_path=str(path),
                translated=translated,
                translation_provider=provider_used,
                source_language=analysis.document.source_language,
                source_chars=len(raw_text),
                translated_chars=len(translated_text),
                event_count=len(analysis.document.extracted_events),
                beat_count=len(analysis.document.story_beats),
                theme_count=len(analysis.document.theme_signals),
                insight_count=len(analysis.document.insights),
                top_entities=top_entities,
                top_themes=top_themes,
                quality_passed=analysis.document.quality_gate.passed,
                translation_quality=analysis.document.quality_gate.translation_quality,
                timing_seconds=analysis.timing,
            )
            _write_json(summary_path, asdict(chapter_summary))
            chapter_summaries.append(chapter_summary)
            processed += 1
            for key, value in analysis.timing.items():
                timing_totals[key] = timing_totals.get(key, 0.0) + value
        except Exception as exc:  # noqa: BLE001
            failed += 1
            failures.append({"chapter_number": number, "stage": "analyze", "error": str(exc)})
            if args.strict:
                raise

    finished_at = datetime.now(UTC).isoformat()
    elapsed = time.perf_counter() - started
    average = elapsed / processed if processed else 0.0
    batch_summary = BatchSummary(
        run_id=args.run_id,
        started_at_utc=started_at,
        finished_at_utc=finished_at,
        total_chapters=len(filtered),
        processed_chapters=processed,
        skipped_chapters=skipped,
        failed_chapters=failed,
        failures=failures,
        elapsed_seconds=round(elapsed, 2),
        average_chapter_seconds=round(average, 2),
        translation_provider=args.translate_provider,
        timing_totals={key: round(value, 3) for key, value in timing_totals.items()},
    )
    _write_json(output_root / "summary.json", asdict(batch_summary))
    dashboard_payload = _dashboard_payload(
        run_summary=batch_summary,
        chapter_summaries=chapter_summaries,
    )
    _write_json(output_root / "dashboard.json", dashboard_payload)
    if args.dashboard_path:
        _write_json(Path(args.dashboard_path), dashboard_payload)
    return batch_summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run story analysis in batch over chapter files.")
    parser.add_argument("--source-dir", required=True)
    parser.add_argument("--output-dir", default="work/pipeline_runs")
    parser.add_argument("--run-id", default="batch-run")
    parser.add_argument("--translated-dir", default="")
    parser.add_argument("--chapter-start", type=int, default=1)
    parser.add_argument("--chapter-end", type=int, default=0)
    parser.add_argument("--max-chapters", type=int, default=0)
    parser.add_argument(
        "--translate-provider",
        choices=["none", "argos", "libretranslate", "chain"],
        default="chain",
    )
    parser.add_argument("--source-language", default="ja")
    parser.add_argument("--target-language", default="en")
    parser.add_argument("--libretranslate-url", default="http://localhost:5000")
    parser.add_argument("--libretranslate-api-key", default="")
    parser.add_argument("--translate-delay-seconds", type=float, default=0.35)
    parser.add_argument("--translate-chunk-size", type=int, default=1800)
    parser.add_argument("--mode", choices=["translate", "analyze", "all"], default="all")
    parser.add_argument("--story-id-prefix", default="chapter-")
    parser.add_argument("--dashboard-path", default="")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--strict", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    if not args.run_id.strip():
        args.run_id = "batch-run"
    args.chapter_start = max(1, int(args.chapter_start))
    args.chapter_end = int(args.chapter_end) if int(args.chapter_end) > 0 else 0
    args.max_chapters = int(args.max_chapters) if int(args.max_chapters) > 0 else 0
    args.translated_dir = str(args.translated_dir).strip()
    args.dashboard_path = str(args.dashboard_path).strip()
    run_pipeline_batch(args)


if __name__ == "__main__":
    main()
