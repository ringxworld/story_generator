from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from story_gen.core.story_feature_pipeline import ChapterFeatureInput
from story_gen.native.feature_metrics import (
    NativeFeatureMetrics,
    NativeFeatureMetricsError,
    compute_native_feature_metrics,
    extract_story_features_native,
)


def test_compute_native_feature_metrics_parses_json(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(
        command: list[str],
        *,
        input: str,
        text: bool,
        capture_output: bool,
        check: bool,
        timeout: float,
    ) -> subprocess.CompletedProcess[str]:
        del command, input, text, capture_output, check, timeout
        return subprocess.CompletedProcess(
            args=["story_feature_metrics"],
            returncode=0,
            stdout=(
                '{"source_length_chars": 42, "sentence_count": 2, "token_count": 12, '
                '"avg_sentence_length": 6.0, "dialogue_line_ratio": 0.25}'
            ),
            stderr="",
        )

    monkeypatch.setattr("story_gen.native.feature_metrics.subprocess.run", fake_run)
    metrics = compute_native_feature_metrics(
        text="Sample text.",
        executable=Path("story_feature_metrics"),
    )
    assert metrics.source_length_chars == 42
    assert metrics.sentence_count == 2
    assert metrics.token_count == 12
    assert metrics.avg_sentence_length == 6.0
    assert metrics.dialogue_line_ratio == 0.25


def test_compute_native_feature_metrics_raises_on_nonzero_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(
        command: list[str],
        *,
        input: str,
        text: bool,
        capture_output: bool,
        check: bool,
        timeout: float,
    ) -> subprocess.CompletedProcess[str]:
        del command, input, text, capture_output, check, timeout
        return subprocess.CompletedProcess(
            args=["story_feature_metrics"],
            returncode=2,
            stdout="",
            stderr="boom",
        )

    monkeypatch.setattr("story_gen.native.feature_metrics.subprocess.run", fake_run)
    with pytest.raises(NativeFeatureMetricsError, match="exit code 2"):
        compute_native_feature_metrics(
            text="Sample text.",
            executable=Path("story_feature_metrics"),
        )


def test_extract_story_features_native_uses_metric_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_metrics(
        *,
        text: str,
        executable: Path | None = None,
        timeout_seconds: float = 10.0,
    ) -> NativeFeatureMetrics:
        del text, executable, timeout_seconds
        return NativeFeatureMetrics(
            source_length_chars=30,
            sentence_count=2,
            token_count=10,
            avg_sentence_length=5.0,
            dialogue_line_ratio=0.5,
        )

    monkeypatch.setattr(
        "story_gen.native.feature_metrics.resolve_story_feature_metrics_binary",
        lambda: Path("story_feature_metrics"),
    )
    monkeypatch.setattr(
        "story_gen.native.feature_metrics.compute_native_feature_metrics", fake_metrics
    )

    result = extract_story_features_native(
        story_id="story-1",
        chapters=[
            ChapterFeatureInput(
                chapter_key="ch01",
                title="Chapter 1",
                text='"Hello there."\nNarration line.',
            )
        ],
    )
    row = result.chapter_features[0]
    assert row.source_length_chars == 30
    assert row.sentence_count == 2
    assert row.token_count == 10
    assert row.avg_sentence_length == 5.0
    assert row.dialogue_line_ratio == 0.5
    assert row.top_keywords


def test_extract_story_features_native_requires_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "story_gen.native.feature_metrics.resolve_story_feature_metrics_binary", lambda: None
    )
    with pytest.raises(NativeFeatureMetricsError, match="not found"):
        extract_story_features_native(
            story_id="story-1",
            chapters=[
                ChapterFeatureInput(
                    chapter_key="ch01",
                    title="Chapter 1",
                    text="text",
                )
            ],
        )
