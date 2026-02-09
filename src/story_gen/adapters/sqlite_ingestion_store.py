"""SQLite persistence adapter for ingestion job status and retries."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4

from story_gen.core.story_ingestion import IngestionArtifact

IngestionJobState = Literal["processing", "succeeded", "failed"]


@dataclass(frozen=True)
class StoredIngestionJob:
    """Persisted ingestion job metadata for polling and retry semantics."""

    job_id: str
    story_id: str
    owner_id: str
    source_type: str
    idempotency_key: str
    source_hash: str
    dedupe_key: str
    status: IngestionJobState
    attempt_count: int
    retry_count: int
    segment_count: int
    issue_count: int
    run_id: str | None
    last_error: str | None
    created_at_utc: str
    updated_at_utc: str
    completed_at_utc: str | None


class SQLiteIngestionStore:
    """Persist ingestion status with deterministic idempotency dedupe keys."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self._db_path))
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ingestion_jobs (
                    job_id TEXT PRIMARY KEY,
                    story_id TEXT NOT NULL,
                    owner_id TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    source_hash TEXT NOT NULL,
                    dedupe_key TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempt_count INTEGER NOT NULL,
                    retry_count INTEGER NOT NULL,
                    segment_count INTEGER NOT NULL DEFAULT 0,
                    issue_count INTEGER NOT NULL DEFAULT 0,
                    run_id TEXT NULL,
                    last_error TEXT NULL,
                    created_at_utc TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL,
                    completed_at_utc TEXT NULL,
                    UNIQUE(owner_id, story_id, dedupe_key)
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_owner_story
                ON ingestion_jobs(owner_id, story_id, updated_at_utc DESC)
                """
            )

    def _row_to_job(self, row: sqlite3.Row) -> StoredIngestionJob:
        return StoredIngestionJob(
            job_id=str(row["job_id"]),
            story_id=str(row["story_id"]),
            owner_id=str(row["owner_id"]),
            source_type=str(row["source_type"]),
            idempotency_key=str(row["idempotency_key"]),
            source_hash=str(row["source_hash"]),
            dedupe_key=str(row["dedupe_key"]),
            status=str(row["status"]),  # type: ignore[arg-type]
            attempt_count=int(row["attempt_count"]),
            retry_count=int(row["retry_count"]),
            segment_count=int(row["segment_count"]),
            issue_count=int(row["issue_count"]),
            run_id=str(row["run_id"]) if row["run_id"] is not None else None,
            last_error=str(row["last_error"]) if row["last_error"] is not None else None,
            created_at_utc=str(row["created_at_utc"]),
            updated_at_utc=str(row["updated_at_utc"]),
            completed_at_utc=(
                str(row["completed_at_utc"]) if row["completed_at_utc"] is not None else None
            ),
        )

    def begin_job(
        self,
        *,
        owner_id: str,
        story_id: str,
        artifact: IngestionArtifact,
    ) -> tuple[StoredIngestionJob, bool]:
        """Start ingestion attempt and return whether an identical successful job exists."""
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            existing = connection.execute(
                """
                SELECT *
                FROM ingestion_jobs
                WHERE owner_id = ? AND story_id = ? AND dedupe_key = ?
                LIMIT 1
                """,
                (owner_id, story_id, artifact.dedupe_key),
            ).fetchone()
            if existing is None:
                job_id = uuid4().hex
                connection.execute(
                    """
                    INSERT INTO ingestion_jobs (
                        job_id,
                        story_id,
                        owner_id,
                        source_type,
                        idempotency_key,
                        source_hash,
                        dedupe_key,
                        status,
                        attempt_count,
                        retry_count,
                        created_at_utc,
                        updated_at_utc
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'processing', 1, ?, ?, ?)
                    """,
                    (
                        job_id,
                        story_id,
                        owner_id,
                        artifact.source_type,
                        artifact.idempotency_key,
                        artifact.source_hash,
                        artifact.dedupe_key,
                        max(0, artifact.retry_count),
                        now,
                        now,
                    ),
                )
                row = connection.execute(
                    "SELECT * FROM ingestion_jobs WHERE job_id = ? LIMIT 1", (job_id,)
                ).fetchone()
                assert row is not None
                return self._row_to_job(row), False
            retry_count = int(existing["retry_count"]) + 1
            attempt_count = int(existing["attempt_count"]) + 1
            already_succeeded = str(existing["status"]) == "succeeded"
            connection.execute(
                """
                UPDATE ingestion_jobs
                SET
                    status = ?,
                    source_type = ?,
                    idempotency_key = ?,
                    source_hash = ?,
                    dedupe_key = ?,
                    attempt_count = ?,
                    retry_count = ?,
                    last_error = NULL,
                    updated_at_utc = ?
                WHERE job_id = ?
                """,
                (
                    "succeeded" if already_succeeded else "processing",
                    artifact.source_type,
                    artifact.idempotency_key,
                    artifact.source_hash,
                    artifact.dedupe_key,
                    attempt_count,
                    retry_count,
                    now,
                    str(existing["job_id"]),
                ),
            )
            row = connection.execute(
                "SELECT * FROM ingestion_jobs WHERE job_id = ? LIMIT 1",
                (str(existing["job_id"]),),
            ).fetchone()
            assert row is not None
            return self._row_to_job(row), already_succeeded

    def mark_succeeded(
        self,
        *,
        job_id: str,
        segment_count: int,
        issue_count: int,
        run_id: str,
    ) -> StoredIngestionJob:
        """Mark a job successful after analysis persistence completes."""
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE ingestion_jobs
                SET
                    status = 'succeeded',
                    segment_count = ?,
                    issue_count = ?,
                    run_id = ?,
                    last_error = NULL,
                    updated_at_utc = ?,
                    completed_at_utc = ?
                WHERE job_id = ?
                """,
                (segment_count, issue_count, run_id, now, now, job_id),
            )
            row = connection.execute(
                "SELECT * FROM ingestion_jobs WHERE job_id = ? LIMIT 1", (job_id,)
            ).fetchone()
        if row is None:
            raise RuntimeError("Ingestion job not found after success update.")
        return self._row_to_job(row)

    def mark_failed(self, *, job_id: str, error_message: str) -> StoredIngestionJob:
        """Mark a job failed and persist error context for polling surfaces."""
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE ingestion_jobs
                SET
                    status = 'failed',
                    last_error = ?,
                    updated_at_utc = ?,
                    completed_at_utc = ?
                WHERE job_id = ?
                """,
                (error_message[:4000], now, now, job_id),
            )
            row = connection.execute(
                "SELECT * FROM ingestion_jobs WHERE job_id = ? LIMIT 1", (job_id,)
            ).fetchone()
        if row is None:
            raise RuntimeError("Ingestion job not found after failure update.")
        return self._row_to_job(row)

    def get_latest_job(self, *, owner_id: str, story_id: str) -> StoredIngestionJob | None:
        """Return latest ingestion job for one owner/story pair."""
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM ingestion_jobs
                WHERE owner_id = ? AND story_id = ?
                ORDER BY updated_at_utc DESC
                LIMIT 1
                """,
                (owner_id, story_id),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_job(row)
