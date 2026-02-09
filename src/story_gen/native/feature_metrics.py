"""Native acceleration path for chapter-level story feature metrics."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from story_gen.core.story_feature_pipeline import (
    FEATURE_SCHEMA_VERSION,
    ChapterFeatureInput,
    ChapterFeatureRow,
    StoryFeatureExtractionResult,
    _tokenize,
    _top_keywords,
)


class NativeFeatureMetricsError(RuntimeError):
    """Raised when native feature metrics execution fails."""


@dataclass(frozen=True)
class NativeFeatureMetrics:
    """Raw metrics returned from native feature analyzer."""

    source_length_chars: int
    sentence_count: int
    token_count: int
    avg_sentence_length: float
    dialogue_line_ratio: float


def _exe_name(base: str) -> str:
    if sys.platform.startswith("win"):
        return f"{base}.exe"
    return base


def _candidate_binary_paths() -> list[Path]:
    base_name = _exe_name("story_feature_metrics")
    return [
        Path("build/cpp/cpp") / base_name,
        Path("build/cpp/Release") / base_name,
        Path("build/cpp") / base_name,
        Path("build/cpp/cpp/Release") / base_name,
    ]


def resolve_story_feature_metrics_binary() -> Path | None:
    """Resolve the native executable path from env, local build, or PATH."""
    from_env = os.environ.get("STORY_GEN_NATIVE_FEATURE_METRICS_BIN", "").strip()
    if from_env:
        candidate = Path(from_env)
        if candidate.is_file():
            return candidate

    for candidate in _candidate_binary_paths():
        if candidate.is_file():
            return candidate

    from_path = shutil.which("story_feature_metrics")
    if from_path:
        return Path(from_path)
    return None


def compute_native_feature_metrics(
    *,
    text: str,
    executable: Path | None = None,
    timeout_seconds: float = 10.0,
) -> NativeFeatureMetrics:
    """Run the native metric executable and parse one JSON response."""
    resolved = executable if executable is not None else resolve_story_feature_metrics_binary()
    if resolved is None:
        raise NativeFeatureMetricsError(
            "story_feature_metrics executable not found; build native tools or set "
            "STORY_GEN_NATIVE_FEATURE_METRICS_BIN."
        )

    command = [str(resolved)]
    try:
        completed = subprocess.run(
            command,
            input=text,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )
    except OSError as exc:
        raise NativeFeatureMetricsError(f"failed to execute native metrics tool: {exc}") from exc
    except subprocess.TimeoutExpired as exc:
        raise NativeFeatureMetricsError(
            f"native metrics timed out after {timeout_seconds:.1f}s"
        ) from exc

    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        raise NativeFeatureMetricsError(
            f"native metrics failed with exit code {completed.returncode}: {stderr}"
        )

    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise NativeFeatureMetricsError("native metrics returned invalid JSON output") from exc

    try:
        metrics = NativeFeatureMetrics(
            source_length_chars=int(payload["source_length_chars"]),
            sentence_count=int(payload["sentence_count"]),
            token_count=int(payload["token_count"]),
            avg_sentence_length=float(payload["avg_sentence_length"]),
            dialogue_line_ratio=float(payload["dialogue_line_ratio"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise NativeFeatureMetricsError("native metrics response missing required fields") from exc

    if metrics.source_length_chars < 0 or metrics.sentence_count < 0 or metrics.token_count < 0:
        raise NativeFeatureMetricsError("native metrics response contained negative counters")
    if not 0.0 <= metrics.dialogue_line_ratio <= 1.0:
        raise NativeFeatureMetricsError("native metrics dialogue_line_ratio out of range")

    return metrics


def extract_story_features_native(
    *,
    story_id: str,
    chapters: list[ChapterFeatureInput],
    executable: Path | None = None,
) -> StoryFeatureExtractionResult:
    """Extract deterministic chapter features using native metric acceleration."""
    if not chapters:
        raise ValueError("At least one chapter is required for feature extraction.")
    normalized_story_id = story_id.strip()
    if not normalized_story_id:
        raise ValueError("story_id must not be empty.")

    resolved = executable if executable is not None else resolve_story_feature_metrics_binary()
    if resolved is None:
        raise NativeFeatureMetricsError(
            "story_feature_metrics executable not found; build native tools or set "
            "STORY_GEN_NATIVE_FEATURE_METRICS_BIN."
        )

    rows: list[ChapterFeatureRow] = []
    for index, chapter in enumerate(chapters, start=1):
        text = chapter.text.strip()
        if not text:
            raise ValueError(f"Chapter '{chapter.chapter_key}' has empty text.")
        metrics = compute_native_feature_metrics(text=text, executable=resolved)
        if metrics.sentence_count < 1:
            raise ValueError(f"Chapter '{chapter.chapter_key}' has no sentence-like content.")
        if metrics.token_count < 1:
            raise ValueError(f"Chapter '{chapter.chapter_key}' has no tokenizable content.")
        tokens = _tokenize(text)
        rows.append(
            ChapterFeatureRow(
                schema_version=FEATURE_SCHEMA_VERSION,
                story_id=normalized_story_id,
                chapter_key=chapter.chapter_key,
                chapter_index=index,
                source_length_chars=metrics.source_length_chars,
                sentence_count=metrics.sentence_count,
                token_count=metrics.token_count,
                avg_sentence_length=round(metrics.avg_sentence_length, 4),
                dialogue_line_ratio=round(metrics.dialogue_line_ratio, 4),
                top_keywords=_top_keywords(tokens),
            )
        )

    return StoryFeatureExtractionResult(
        schema_version=FEATURE_SCHEMA_VERSION,
        story_id=normalized_story_id,
        extracted_at_utc=datetime.now(UTC).isoformat(),
        chapter_features=rows,
    )
