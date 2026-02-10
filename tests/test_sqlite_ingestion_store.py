from __future__ import annotations

import sqlite3
from pathlib import Path

from story_gen.adapters.sqlite_ingestion_store import SQLiteIngestionStore
from story_gen.core.story_ingestion import IngestionArtifact, IngestionRequest, ingest_story_text


def _artifact(*, key: str, text: str = "Rhea finds the ledger.") -> IngestionArtifact:
    return ingest_story_text(
        IngestionRequest(source_type="text", source_text=text, idempotency_key=key)
    )


def _job_rows(db_path: Path) -> int:
    connection = sqlite3.connect(str(db_path))
    try:
        row = connection.execute("SELECT COUNT(*) FROM ingestion_jobs").fetchone()
        assert row is not None
        return int(row[0])
    finally:
        connection.close()


def test_ingestion_store_dedupes_same_owner_story_and_dedupe_key(tmp_path: Path) -> None:
    db_path = tmp_path / "story.db"
    store = SQLiteIngestionStore(db_path=db_path)
    artifact = _artifact(key="run-1")
    first, deduped_first = store.begin_job(
        owner_id="owner-1", story_id="story-1", artifact=artifact
    )
    assert deduped_first is False
    assert first.status == "processing"
    assert _job_rows(db_path) == 1

    store.mark_succeeded(
        job_id=first.job_id,
        segment_count=len(artifact.segments),
        issue_count=len(artifact.issues),
        run_id="run-abc",
    )
    second, deduped_second = store.begin_job(
        owner_id="owner-1", story_id="story-1", artifact=artifact
    )
    assert deduped_second is True
    assert second.status == "succeeded"
    assert second.attempt_count == 2
    assert _job_rows(db_path) == 1


def test_ingestion_store_retries_failed_job_without_duplicate_row(tmp_path: Path) -> None:
    db_path = tmp_path / "story.db"
    store = SQLiteIngestionStore(db_path=db_path)
    artifact = _artifact(key="run-2")
    started, _ = store.begin_job(owner_id="owner-1", story_id="story-1", artifact=artifact)
    failed = store.mark_failed(job_id=started.job_id, error_message="temporary parse failure")
    assert failed.status == "failed"
    retried, deduped = store.begin_job(owner_id="owner-1", story_id="story-1", artifact=artifact)
    assert deduped is False
    assert retried.status == "processing"
    assert retried.retry_count == failed.retry_count + 1
    assert _job_rows(db_path) == 1


def test_ingestion_store_latest_job_is_owner_scoped(tmp_path: Path) -> None:
    db_path = tmp_path / "story.db"
    store = SQLiteIngestionStore(db_path=db_path)
    artifact = _artifact(key="run-3")
    first, _ = store.begin_job(owner_id="owner-a", story_id="story-1", artifact=artifact)
    store.mark_failed(job_id=first.job_id, error_message="x")
    second, _ = store.begin_job(owner_id="owner-b", story_id="story-1", artifact=artifact)
    store.mark_succeeded(
        job_id=second.job_id,
        segment_count=len(artifact.segments),
        issue_count=0,
        run_id="run-xyz",
    )
    latest_a = store.get_latest_job(owner_id="owner-a", story_id="story-1")
    latest_b = store.get_latest_job(owner_id="owner-b", story_id="story-1")
    assert latest_a is not None and latest_a.owner_id == "owner-a"
    assert latest_b is not None and latest_b.owner_id == "owner-b"
