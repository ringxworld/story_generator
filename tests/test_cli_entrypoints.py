from __future__ import annotations

import runpy

import pytest

from story_gen.cli import app, collect, reference, video
from story_gen.reference_pipeline import PipelineArgs
from story_gen.story_collector import StoryCollectorArgs
from story_gen.youtube_downloader import VideoStoryArgs


def test_cli_app_main_prints_scaffold(capsys: pytest.CaptureFixture[str]) -> None:
    app.main()
    captured = capsys.readouterr()
    assert "story_gen scaffold" in captured.out
    assert "concept dependencies:" in captured.out


def test_collect_main_builds_story_collector_args(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[StoryCollectorArgs] = []
    monkeypatch.setattr(
        "story_gen.cli.collect.run_story_collection", lambda args: seen.append(args)
    )
    collect.main(["--series-code", "n1234ab"])
    assert seen
    assert seen[0].series_code == "n1234ab"


def test_reference_main_builds_pipeline_args(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[PipelineArgs] = []
    monkeypatch.setattr("story_gen.cli.reference.run_pipeline", lambda args: seen.append(args))
    reference.main(["--project-id", "n2267be", "--max-episodes", "1"])
    assert seen
    assert seen[0].project_id == "n2267be"


def test_video_main_builds_video_story_args(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[VideoStoryArgs] = []
    monkeypatch.setattr(
        "story_gen.cli.video.run_video_story_pipeline", lambda args: seen.append(args)
    )
    video.main(["--url", "https://example.com/video"])
    assert seen
    assert seen[0].url == "https://example.com/video"


def test_package_main_module_executes_cli_main(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {"value": False}

    def fake_main() -> None:
        called["value"] = True

    monkeypatch.setattr("story_gen.cli.main", fake_main)
    runpy.run_module("story_gen.cli.__main__", run_name="__main__")
    assert called["value"] is True
