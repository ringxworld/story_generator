from __future__ import annotations

import runpy
from pathlib import Path

import pytest

from story_gen.cli import app, collect, pre_push, reference, site, video


def test_cli_app_main_prints_scaffold(capsys: pytest.CaptureFixture[str]) -> None:
    app.main()
    captured = capsys.readouterr()
    assert "story_gen scaffold" in captured.out
    assert "concept dependencies:" in captured.out


def test_collect_main_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[list[str] | None] = []
    monkeypatch.setattr(
        "story_gen.cli.collect.cli_main",
        lambda argv=None: seen.append(argv),
    )
    collect.main(["--series-code", "n1234ab"])
    assert seen == [["--series-code", "n1234ab"]]


def test_reference_main_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[list[str] | None] = []
    monkeypatch.setattr(
        "story_gen.cli.reference.cli_main",
        lambda argv=None: seen.append(argv),
    )
    reference.main(["--project-id", "demo"])
    assert seen == [["--project-id", "demo"]]


def test_video_main_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[list[str] | None] = []
    monkeypatch.setattr(
        "story_gen.cli.video.cli_main",
        lambda argv=None: seen.append(argv),
    )
    video.main(["--url", "https://example.com/video"])
    assert seen == [["--url", "https://example.com/video"]]


def test_pre_push_main_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {"value": False}

    def fake_run_checks() -> None:
        called["value"] = True

    monkeypatch.setattr("story_gen.cli.pre_push.run_checks", fake_run_checks)
    pre_push.main()
    assert called["value"] is True


def test_site_main_builds_and_reports_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    expected = tmp_path / "index.html"
    monkeypatch.setattr("story_gen.cli.site.build_site", lambda: expected)
    site.main()
    captured = capsys.readouterr()
    assert str(expected) in captured.out


def test_package_main_module_executes_cli_main(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {"value": False}

    def fake_main() -> None:
        called["value"] = True

    monkeypatch.setattr("story_gen.cli.main", fake_main)
    runpy.run_module("story_gen.cli.__main__", run_name="__main__")
    assert called["value"] is True
