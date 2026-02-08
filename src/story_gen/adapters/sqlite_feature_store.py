"""SQLite persistence adapter for extracted story feature rows."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from story_gen.core.story_feature_pipeline import (
    FEATURE_SCHEMA_VERSION,
    ChapterFeatureRow,
    StoryFeatureExtractionResult,
)


@dataclass(frozen=True)
class StoredFeatureRun:
    """Persisted feature extraction run metadata."""

    run_id: str
    story_id: str
    owner_id: str
    schema_version: str
    extracted_at_utc: str


class SQLiteFeatureStore:
    """Persist and query story feature extraction runs."""

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
                CREATE TABLE IF NOT EXISTS feature_schema_versions (
                    schema_key TEXT PRIMARY KEY,
                    schema_version TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS story_feature_runs (
                    run_id TEXT PRIMARY KEY,
                    story_id TEXT NOT NULL,
                    owner_id TEXT NOT NULL,
                    schema_version TEXT NOT NULL,
                    extracted_at_utc TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS story_feature_rows (
                    run_id TEXT NOT NULL,
                    story_id TEXT NOT NULL,
                    chapter_key TEXT NOT NULL,
                    chapter_index INTEGER NOT NULL,
                    source_length_chars INTEGER NOT NULL,
                    sentence_count INTEGER NOT NULL,
                    token_count INTEGER NOT NULL,
                    avg_sentence_length REAL NOT NULL,
                    dialogue_line_ratio REAL NOT NULL,
                    top_keywords_json TEXT NOT NULL,
                    PRIMARY KEY (run_id, chapter_key),
                    FOREIGN KEY (run_id) REFERENCES story_feature_runs(run_id)
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_story_feature_runs_owner_story
                ON story_feature_runs(owner_id, story_id, extracted_at_utc DESC)
                """
            )

    def _ensure_schema_version(self) -> None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT schema_version
                FROM feature_schema_versions
                WHERE schema_key = 'story_feature_rows'
                """
            ).fetchone()
            if row is None:
                connection.execute(
                    """
                    INSERT INTO feature_schema_versions (schema_key, schema_version, updated_at_utc)
                    VALUES (?, ?, ?)
                    """,
                    ("story_feature_rows", FEATURE_SCHEMA_VERSION, datetime.now(UTC).isoformat()),
                )
                return
            existing_version = str(row["schema_version"])
            if existing_version != FEATURE_SCHEMA_VERSION:
                raise RuntimeError(
                    "Feature schema version mismatch: "
                    f"database={existing_version}, expected={FEATURE_SCHEMA_VERSION}"
                )

    def write_feature_result(
        self,
        *,
        owner_id: str,
        result: StoryFeatureExtractionResult,
    ) -> StoredFeatureRun:
        """Persist one extraction run and all chapter rows."""
        run_id = uuid4().hex
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO story_feature_runs (run_id, story_id, owner_id, schema_version, extracted_at_utc)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    result.story_id,
                    owner_id,
                    result.schema_version,
                    result.extracted_at_utc,
                ),
            )
            for row in result.chapter_features:
                connection.execute(
                    """
                    INSERT INTO story_feature_rows (
                        run_id,
                        story_id,
                        chapter_key,
                        chapter_index,
                        source_length_chars,
                        sentence_count,
                        token_count,
                        avg_sentence_length,
                        dialogue_line_ratio,
                        top_keywords_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        row.story_id,
                        row.chapter_key,
                        row.chapter_index,
                        row.source_length_chars,
                        row.sentence_count,
                        row.token_count,
                        row.avg_sentence_length,
                        row.dialogue_line_ratio,
                        json.dumps(row.top_keywords, ensure_ascii=False),
                    ),
                )
        return StoredFeatureRun(
            run_id=run_id,
            story_id=result.story_id,
            owner_id=owner_id,
            schema_version=result.schema_version,
            extracted_at_utc=result.extracted_at_utc,
        )

    def get_latest_feature_result(
        self,
        *,
        owner_id: str,
        story_id: str,
    ) -> tuple[StoredFeatureRun, StoryFeatureExtractionResult] | None:
        """Load the latest feature run for one owner/story pair."""
        with self._connect() as connection:
            run_row = connection.execute(
                """
                SELECT run_id, story_id, owner_id, schema_version, extracted_at_utc
                FROM story_feature_runs
                WHERE owner_id = ? AND story_id = ?
                ORDER BY extracted_at_utc DESC
                LIMIT 1
                """,
                (owner_id, story_id),
            ).fetchone()
            if run_row is None:
                return None
            run_id = str(run_row["run_id"])
            row_rows = connection.execute(
                """
                SELECT
                    story_id,
                    chapter_key,
                    chapter_index,
                    source_length_chars,
                    sentence_count,
                    token_count,
                    avg_sentence_length,
                    dialogue_line_ratio,
                    top_keywords_json
                FROM story_feature_rows
                WHERE run_id = ?
                ORDER BY chapter_index ASC
                """,
                (run_id,),
            ).fetchall()
        chapter_features = [
            ChapterFeatureRow(
                schema_version=FEATURE_SCHEMA_VERSION,
                story_id=str(row["story_id"]),
                chapter_key=str(row["chapter_key"]),
                chapter_index=int(row["chapter_index"]),
                source_length_chars=int(row["source_length_chars"]),
                sentence_count=int(row["sentence_count"]),
                token_count=int(row["token_count"]),
                avg_sentence_length=float(row["avg_sentence_length"]),
                dialogue_line_ratio=float(row["dialogue_line_ratio"]),
                top_keywords=json.loads(str(row["top_keywords_json"])),
            )
            for row in row_rows
        ]
        result = StoryFeatureExtractionResult(
            schema_version=FEATURE_SCHEMA_VERSION,
            story_id=story_id,
            extracted_at_utc=str(run_row["extracted_at_utc"]),
            chapter_features=chapter_features,
        )
        return (
            StoredFeatureRun(
                run_id=run_id,
                story_id=str(run_row["story_id"]),
                owner_id=str(run_row["owner_id"]),
                schema_version=str(run_row["schema_version"]),
                extracted_at_utc=str(run_row["extracted_at_utc"]),
            ),
            result,
        )
