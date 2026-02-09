from __future__ import annotations

import os
import runpy
from pathlib import Path

import pytest

from story_gen.adapters.sqlite_feature_store import SQLiteFeatureStore
from story_gen.adapters.sqlite_story_analysis_store import SQLiteStoryAnalysisStore
from story_gen.adapters.sqlite_story_store import SQLiteStoryStore
from story_gen.api.contracts import StoryBlueprint
from story_gen.cli import api as api_cli
from story_gen.cli import (
    app,
    blueprint,
    dashboard_export,
    features,
    reference_pipeline,
    story_collector,
    youtube_downloader,
)
from story_gen.cli.reference_pipeline import PipelineArgs
from story_gen.cli.story_collector import StoryCollectorArgs
from story_gen.cli.youtube_downloader import VideoStoryArgs
from story_gen.core.story_analysis_pipeline import run_story_analysis
from story_gen.core.story_feature_pipeline import (
    FEATURE_SCHEMA_VERSION,
    ChapterFeatureRow,
    StoryFeatureExtractionResult,
)


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


def test_blueprint_cli_validates_and_rewrites_json(tmp_path: Path) -> None:
    path = tmp_path / "blueprint.json"
    raw = StoryBlueprint(
        premise="Premise",
        themes=[],
        characters=[],
        chapters=[],
        canon_rules=[],
    )
    path.write_text(raw.model_dump_json(), encoding="utf-8")
    blueprint.main(["--input", str(path)])
    reparsed = StoryBlueprint.model_validate_json(path.read_text(encoding="utf-8"))
    assert reparsed.premise == "Premise"


def test_features_cli_extracts_and_persists_rows(tmp_path: Path) -> None:
    db_path = tmp_path / "stories.db"
    story_store = SQLiteStoryStore(db_path=db_path)
    user = story_store.create_user(
        email="alice@example.com",
        display_name="Alice",
        password_hash="hash",
    )
    assert user is not None
    blueprint_payload = StoryBlueprint.model_validate(
        {
            "premise": "Premise",
            "themes": [{"key": "memory", "statement": "x", "priority": 1}],
            "characters": [{"key": "rhea", "role": "investigator", "motivation": "find"}],
            "chapters": [
                {
                    "key": "ch01",
                    "title": "Chapter 1",
                    "objective": "Introduce contradiction.",
                    "required_themes": ["memory"],
                    "participating_characters": ["rhea"],
                    "prerequisites": [],
                    "draft_text": "Sample text. Another sentence.",
                }
            ],
            "canon_rules": [],
        }
    )
    story = story_store.create_story(
        owner_id=user.user_id,
        title="Story",
        blueprint_json=blueprint_payload.model_dump_json(),
    )

    features.main(
        [
            "--db-path",
            str(db_path),
            "--story-id",
            story.story_id,
            "--owner-id",
            user.user_id,
        ]
    )
    feature_store = SQLiteFeatureStore(db_path=db_path)
    latest = feature_store.get_latest_feature_result(owner_id=user.user_id, story_id=story.story_id)
    assert latest is not None


def test_features_cli_supports_native_engine(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "stories.db"
    story_store = SQLiteStoryStore(db_path=db_path)
    user = story_store.create_user(
        email="alice@example.com",
        display_name="Alice",
        password_hash="hash",
    )
    assert user is not None
    blueprint_payload = StoryBlueprint.model_validate(
        {
            "premise": "Premise",
            "themes": [{"key": "memory", "statement": "x", "priority": 1}],
            "characters": [{"key": "rhea", "role": "investigator", "motivation": "find"}],
            "chapters": [
                {
                    "key": "ch01",
                    "title": "Chapter 1",
                    "objective": "Introduce contradiction.",
                    "required_themes": ["memory"],
                    "participating_characters": ["rhea"],
                    "prerequisites": [],
                    "draft_text": "Sample text. Another sentence.",
                }
            ],
            "canon_rules": [],
        }
    )
    story = story_store.create_story(
        owner_id=user.user_id,
        title="Story",
        blueprint_json=blueprint_payload.model_dump_json(),
    )

    def fake_native_extract(
        *, story_id: str, chapters: list[object]
    ) -> StoryFeatureExtractionResult:
        del chapters
        return StoryFeatureExtractionResult(
            schema_version=FEATURE_SCHEMA_VERSION,
            story_id=story_id,
            extracted_at_utc="2026-01-01T00:00:00+00:00",
            chapter_features=[
                ChapterFeatureRow(
                    schema_version=FEATURE_SCHEMA_VERSION,
                    story_id=story_id,
                    chapter_key="ch01",
                    chapter_index=1,
                    source_length_chars=30,
                    sentence_count=2,
                    token_count=4,
                    avg_sentence_length=2.0,
                    dialogue_line_ratio=0.0,
                    top_keywords=["sample"],
                )
            ],
        )

    monkeypatch.setattr("story_gen.cli.features.extract_story_features_native", fake_native_extract)
    features.main(
        [
            "--db-path",
            str(db_path),
            "--story-id",
            story.story_id,
            "--owner-id",
            user.user_id,
            "--engine",
            "native",
        ]
    )

    feature_store = SQLiteFeatureStore(db_path=db_path)
    latest = feature_store.get_latest_feature_result(owner_id=user.user_id, story_id=story.story_id)
    assert latest is not None


def test_dashboard_export_cli_writes_svg_and_png(tmp_path: Path) -> None:
    db_path = tmp_path / "stories.db"
    story_store = SQLiteStoryStore(db_path=db_path)
    analysis_store = SQLiteStoryAnalysisStore(db_path=db_path)
    user = story_store.create_user(
        email="alice@example.com",
        display_name="Alice",
        password_hash="hash",
    )
    assert user is not None
    blueprint_payload = StoryBlueprint.model_validate(
        {
            "premise": "Premise",
            "themes": [{"key": "memory", "statement": "x", "priority": 1}],
            "characters": [{"key": "rhea", "role": "investigator", "motivation": "find"}],
            "chapters": [
                {
                    "key": "ch01",
                    "title": "Chapter 1",
                    "objective": "Introduce contradiction.",
                    "required_themes": ["memory"],
                    "participating_characters": ["rhea"],
                    "prerequisites": [],
                    "draft_text": "Sample text. Another sentence.",
                }
            ],
            "canon_rules": [],
        }
    )
    story = story_store.create_story(
        owner_id=user.user_id,
        title="Story",
        blueprint_json=blueprint_payload.model_dump_json(),
    )
    analysis = run_story_analysis(
        story_id=story.story_id,
        source_text="Rhea enters the archive and confronts the council.",
    )
    analysis_store.write_analysis_result(owner_id=user.user_id, result=analysis)

    svg_path = tmp_path / "graph.svg"
    dashboard_export.main(
        [
            "--db-path",
            str(db_path),
            "--story-id",
            story.story_id,
            "--owner-id",
            user.user_id,
            "--format",
            "svg",
            "--output",
            str(svg_path),
        ]
    )
    assert svg_path.read_text(encoding="utf-8").startswith("<svg")

    png_path = tmp_path / "graph.png"
    second_png_path = tmp_path / "graph-second.png"
    dashboard_export.main(
        [
            "--db-path",
            str(db_path),
            "--story-id",
            story.story_id,
            "--owner-id",
            user.user_id,
            "--format",
            "png",
            "--output",
            str(png_path),
        ]
    )
    dashboard_export.main(
        [
            "--db-path",
            str(db_path),
            "--story-id",
            story.story_id,
            "--owner-id",
            user.user_id,
            "--format",
            "png",
            "--output",
            str(second_png_path),
        ]
    )
    first_png = png_path.read_bytes()
    second_png = second_png_path.read_bytes()
    assert first_png.startswith(b"\x89PNG\r\n\x1a\n")
    assert first_png == second_png

    timeline_svg_path = tmp_path / "timeline.svg"
    dashboard_export.main(
        [
            "--db-path",
            str(db_path),
            "--story-id",
            story.story_id,
            "--owner-id",
            user.user_id,
            "--view",
            "timeline",
            "--format",
            "svg",
            "--output",
            str(timeline_svg_path),
        ]
    )
    assert timeline_svg_path.read_text(encoding="utf-8").startswith("<svg")

    timeline_png_path = tmp_path / "timeline.png"
    timeline_png_second_path = tmp_path / "timeline-second.png"
    dashboard_export.main(
        [
            "--db-path",
            str(db_path),
            "--story-id",
            story.story_id,
            "--owner-id",
            user.user_id,
            "--view",
            "timeline",
            "--format",
            "png",
            "--output",
            str(timeline_png_path),
        ]
    )
    dashboard_export.main(
        [
            "--db-path",
            str(db_path),
            "--story-id",
            story.story_id,
            "--owner-id",
            user.user_id,
            "--view",
            "timeline",
            "--format",
            "png",
            "--output",
            str(timeline_png_second_path),
        ]
    )
    timeline_first_png = timeline_png_path.read_bytes()
    timeline_second_png = timeline_png_second_path.read_bytes()
    assert timeline_first_png.startswith(b"\x89PNG\r\n\x1a\n")
    assert timeline_first_png == timeline_second_png

    heatmap_svg_path = tmp_path / "theme-heatmap.svg"
    dashboard_export.main(
        [
            "--db-path",
            str(db_path),
            "--story-id",
            story.story_id,
            "--owner-id",
            user.user_id,
            "--view",
            "theme-heatmap",
            "--format",
            "svg",
            "--output",
            str(heatmap_svg_path),
        ]
    )
    assert heatmap_svg_path.read_text(encoding="utf-8").startswith("<svg")

    heatmap_png_path = tmp_path / "theme-heatmap.png"
    heatmap_png_second_path = tmp_path / "theme-heatmap-second.png"
    dashboard_export.main(
        [
            "--db-path",
            str(db_path),
            "--story-id",
            story.story_id,
            "--owner-id",
            user.user_id,
            "--view",
            "theme-heatmap",
            "--format",
            "png",
            "--output",
            str(heatmap_png_path),
        ]
    )
    dashboard_export.main(
        [
            "--db-path",
            str(db_path),
            "--story-id",
            story.story_id,
            "--owner-id",
            user.user_id,
            "--view",
            "theme-heatmap",
            "--format",
            "png",
            "--output",
            str(heatmap_png_second_path),
        ]
    )
    heatmap_first_png = heatmap_png_path.read_bytes()
    heatmap_second_png = heatmap_png_second_path.read_bytes()
    assert heatmap_first_png.startswith(b"\x89PNG\r\n\x1a\n")
    assert heatmap_first_png == heatmap_second_png


def test_dashboard_export_cli_rejects_owner_mismatch(tmp_path: Path) -> None:
    db_path = tmp_path / "stories.db"
    story_store = SQLiteStoryStore(db_path=db_path)
    user = story_store.create_user(
        email="alice@example.com",
        display_name="Alice",
        password_hash="hash",
    )
    assert user is not None
    blueprint_payload = StoryBlueprint.model_validate(
        {
            "premise": "Premise",
            "themes": [{"key": "memory", "statement": "x", "priority": 1}],
            "characters": [{"key": "rhea", "role": "investigator", "motivation": "find"}],
            "chapters": [],
            "canon_rules": [],
        }
    )
    story = story_store.create_story(
        owner_id=user.user_id,
        title="Story",
        blueprint_json=blueprint_payload.model_dump_json(),
    )

    with pytest.raises(SystemExit, match="Owner mismatch"):
        dashboard_export.main(
            [
                "--db-path",
                str(db_path),
                "--story-id",
                story.story_id,
                "--owner-id",
                "another-owner",
                "--output",
                str(tmp_path / "graph.svg"),
            ]
        )


def test_dashboard_export_cli_fails_when_requested_view_payload_is_missing(tmp_path: Path) -> None:
    import sqlite3

    db_path = tmp_path / "stories.db"
    story_store = SQLiteStoryStore(db_path=db_path)
    analysis_store = SQLiteStoryAnalysisStore(db_path=db_path)
    user = story_store.create_user(
        email="alice@example.com",
        display_name="Alice",
        password_hash="hash",
    )
    assert user is not None
    blueprint_payload = StoryBlueprint.model_validate(
        {
            "premise": "Premise",
            "themes": [{"key": "memory", "statement": "x", "priority": 1}],
            "characters": [{"key": "rhea", "role": "investigator", "motivation": "find"}],
            "chapters": [],
            "canon_rules": [],
        }
    )
    story = story_store.create_story(
        owner_id=user.user_id,
        title="Story",
        blueprint_json=blueprint_payload.model_dump_json(),
    )
    analysis = run_story_analysis(
        story_id=story.story_id,
        source_text="Rhea enters the archive and confronts the council.",
    )
    analysis_store.write_analysis_result(owner_id=user.user_id, result=analysis)

    with sqlite3.connect(str(db_path)) as connection:
        connection.execute(
            """
            UPDATE story_analysis_runs
            SET dashboard_json = ?
            WHERE story_id = ?
            """,
            ('{"overview": {}}', story.story_id),
        )
        connection.commit()

    with pytest.raises(SystemExit, match="missing timeline_lanes"):
        dashboard_export.main(
            [
                "--db-path",
                str(db_path),
                "--story-id",
                story.story_id,
                "--owner-id",
                user.user_id,
                "--view",
                "timeline",
                "--format",
                "png",
                "--output",
                str(tmp_path / "timeline.png"),
            ]
        )


def test_dashboard_export_cli_fails_on_unknown_heatmap_stage(tmp_path: Path) -> None:
    import sqlite3

    db_path = tmp_path / "stories.db"
    story_store = SQLiteStoryStore(db_path=db_path)
    analysis_store = SQLiteStoryAnalysisStore(db_path=db_path)
    user = story_store.create_user(
        email="alice@example.com",
        display_name="Alice",
        password_hash="hash",
    )
    assert user is not None
    blueprint_payload = StoryBlueprint.model_validate(
        {
            "premise": "Premise",
            "themes": [{"key": "memory", "statement": "x", "priority": 1}],
            "characters": [{"key": "rhea", "role": "investigator", "motivation": "find"}],
            "chapters": [],
            "canon_rules": [],
        }
    )
    story = story_store.create_story(
        owner_id=user.user_id,
        title="Story",
        blueprint_json=blueprint_payload.model_dump_json(),
    )
    analysis = run_story_analysis(
        story_id=story.story_id,
        source_text="Rhea enters the archive and confronts the council.",
    )
    analysis_store.write_analysis_result(owner_id=user.user_id, result=analysis)

    with sqlite3.connect(str(db_path)) as connection:
        connection.execute(
            """
            UPDATE story_analysis_runs
            SET dashboard_json = ?
            WHERE story_id = ?
            """,
            (
                ('{"theme_heatmap": [{"theme": "memory", "stage": "epilogue", "intensity": 0.6}]}'),
                story.story_id,
            ),
        )
        connection.commit()

    with pytest.raises(SystemExit, match="unsupported stage"):
        dashboard_export.main(
            [
                "--db-path",
                str(db_path),
                "--story-id",
                story.story_id,
                "--owner-id",
                user.user_id,
                "--view",
                "theme-heatmap",
                "--format",
                "png",
                "--output",
                str(tmp_path / "theme-heatmap.png"),
            ]
        )
