from __future__ import annotations

import os
import runpy

import pytest

from story_gen.cli import api as api_cli
from story_gen.cli import app, reference_pipeline, story_collector, youtube_downloader
from story_gen.cli.reference_pipeline import PipelineArgs
from story_gen.cli.story_collector import StoryCollectorArgs
from story_gen.cli.youtube_downloader import VideoStoryArgs


def test_cli_app_main_prints_scaffold(capsys: pytest.CaptureFixture[str]) -> None:
    app.main()
    captured = capsys.readouterr()
    assert "story_gen scaffold" in captured.out
    assert "concept dependencies:" in captured.out


def test_collect_main_builds_story_collector_args(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[StoryCollectorArgs] = []
    monkeypatch.setattr(
        "story_gen.cli.story_collector.run_story_collection",
        lambda args: seen.append(args),
    )
    story_collector.main(["--series-code", "n1234ab"])
    assert seen
    assert seen[0].series_code == "n1234ab"


def test_reference_main_builds_pipeline_args(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[PipelineArgs] = []
    monkeypatch.setattr(
        "story_gen.cli.reference_pipeline.run_pipeline",
        lambda args: seen.append(args),
    )
    reference_pipeline.main(["--project-id", "n2267be", "--max-episodes", "1"])
    assert seen
    assert seen[0].project_id == "n2267be"


def test_video_main_builds_video_story_args(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[VideoStoryArgs] = []
    monkeypatch.setattr(
        "story_gen.cli.youtube_downloader.run_video_story_pipeline",
        lambda args: seen.append(args),
    )
    youtube_downloader.main(["--url", "https://example.com/video"])
    assert seen
    assert seen[0].url == "https://example.com/video"


def test_package_main_module_executes_cli_main(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {"value": False}

    def fake_main() -> None:
        called["value"] = True

    monkeypatch.setattr("story_gen.cli.main", fake_main)
    runpy.run_module("story_gen.cli.__main__", run_name="__main__")
    assert called["value"] is True


def test_api_cli_calls_uvicorn(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_run(app: str, host: str, port: int, reload: bool) -> None:
        calls.append({"app": app, "host": host, "port": port, "reload": reload})

    monkeypatch.setattr("story_gen.cli.api.uvicorn.run", fake_run)
    api_cli.main(["--host", "0.0.0.0", "--port", "9000", "--reload"])

    assert calls == [
        {
            "app": "story_gen.api.app:app",
            "host": "0.0.0.0",
            "port": 9000,
            "reload": True,
        }
    ]


def test_api_cli_sets_db_path_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STORY_GEN_DB_PATH", raising=False)
    monkeypatch.setattr("story_gen.cli.api.uvicorn.run", lambda *args, **kwargs: None)
    api_cli.main(["--db-path", "work/local/custom.db"])
    assert os.environ["STORY_GEN_DB_PATH"] == "work/local/custom.db"
