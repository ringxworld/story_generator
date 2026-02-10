"""SQLite persistence adapter for story intelligence analysis runs."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from story_gen.adapters.story_analysis_store_types import LatestAnalysisPayload, StoredAnalysisRun
from story_gen.core.story_analysis_pipeline import StoryAnalysisResult
from story_gen.core.story_schema import STORY_SCHEMA_VERSION, StoryDocument


class SQLiteStoryAnalysisStore:
    """Persist complete story intelligence outputs for dashboard/API reads."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()
        self._ensure_schema_version()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self._db_path))
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS analysis_schema_versions (
                    schema_key TEXT PRIMARY KEY,
                    schema_version TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS story_analysis_runs (
                    run_id TEXT PRIMARY KEY,
                    story_id TEXT NOT NULL,
                    owner_id TEXT NOT NULL,
                    schema_version TEXT NOT NULL,
                    analyzed_at_utc TEXT NOT NULL,
                    analysis_json TEXT NOT NULL,
                    dashboard_json TEXT NOT NULL,
                    graph_svg TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_story_analysis_owner_story
                ON story_analysis_runs(owner_id, story_id, analyzed_at_utc DESC)
                """
            )

    def _ensure_schema_version(self) -> None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT schema_version
                FROM analysis_schema_versions
                WHERE schema_key = 'story_analysis_runs'
                """
            ).fetchone()
            if row is None:
                connection.execute(
                    """
                    INSERT INTO analysis_schema_versions (schema_key, schema_version, updated_at_utc)
                    VALUES (?, ?, ?)
                    """,
                    ("story_analysis_runs", STORY_SCHEMA_VERSION, datetime.now(UTC).isoformat()),
                )
                return
            existing_version = str(row["schema_version"])
            if existing_version != STORY_SCHEMA_VERSION:
                raise RuntimeError(
                    "Analysis schema version mismatch: "
                    f"database={existing_version}, expected={STORY_SCHEMA_VERSION}"
                )

    def write_analysis_result(
        self,
        *,
        owner_id: str,
        result: StoryAnalysisResult,
    ) -> StoredAnalysisRun:
        """Persist one analysis run and associated dashboard payloads."""
        run_id = uuid4().hex
        analyzed_at_utc = datetime.now(UTC).isoformat()
        analysis_json = result.document.model_dump_json()
        dashboard_json = json.dumps(asdict(result.dashboard), ensure_ascii=False)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO story_analysis_runs (
                    run_id,
                    story_id,
                    owner_id,
                    schema_version,
                    analyzed_at_utc,
                    analysis_json,
                    dashboard_json,
                    graph_svg
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    result.document.story_id,
                    owner_id,
                    result.document.schema_version,
                    analyzed_at_utc,
                    analysis_json,
                    dashboard_json,
                    result.graph_svg,
                ),
            )
        return StoredAnalysisRun(
            run_id=run_id,
            story_id=result.document.story_id,
            owner_id=owner_id,
            schema_version=result.document.schema_version,
            analyzed_at_utc=analyzed_at_utc,
        )

    def get_latest_analysis(
        self,
        *,
        owner_id: str,
        story_id: str,
    ) -> LatestAnalysisPayload | None:
        """Load latest analysis run for one owner/story pair."""
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    run_id,
                    story_id,
                    owner_id,
                    schema_version,
                    analyzed_at_utc,
                    analysis_json,
                    dashboard_json,
                    graph_svg
                FROM story_analysis_runs
                WHERE owner_id = ? AND story_id = ?
                ORDER BY analyzed_at_utc DESC
                LIMIT 1
                """,
                (owner_id, story_id),
            ).fetchone()
        if row is None:
            return None
        metadata = StoredAnalysisRun(
            run_id=str(row["run_id"]),
            story_id=str(row["story_id"]),
            owner_id=str(row["owner_id"]),
            schema_version=str(row["schema_version"]),
            analyzed_at_utc=str(row["analyzed_at_utc"]),
        )
        document = StoryDocument.model_validate_json(str(row["analysis_json"]))
        dashboard = json.loads(str(row["dashboard_json"]))
        graph_svg = str(row["graph_svg"])
        return metadata, document, dashboard, graph_svg
