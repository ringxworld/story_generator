from __future__ import annotations

from pathlib import Path

import pytest

from story_gen.adapters.sqlite_anomaly_store import SQLiteAnomalyStore


def test_anomaly_store_write_and_list_recent(tmp_path: Path) -> None:
    store = SQLiteAnomalyStore(db_path=tmp_path / "anomalies.db")
    first = store.write_anomaly(
        scope="analysis",
        code="quality_warning",
        severity="warning",
        message="Quality gate warning.",
        metadata={"story_id": "story-1"},
    )
    second = store.write_anomaly(
        scope="api",
        code="runtime_error",
        severity="error",
        message="Unhandled exception.",
        metadata={"path": "/api/v1/stories"},
    )

    listed = store.list_recent(limit=10)
    assert len(listed) == 2
    assert listed[0].anomaly_id == second.anomaly_id
    assert listed[1].anomaly_id == first.anomaly_id
    assert "story-1" in listed[1].metadata_json


def test_anomaly_store_prunes_overflow_rows(tmp_path: Path) -> None:
    store = SQLiteAnomalyStore(db_path=tmp_path / "anomalies.db")
    for index in range(7):
        store.write_anomaly(
            scope="analysis",
            code=f"code_{index}",
            severity="warning",
            message=f"event {index}",
            metadata={"index": index},
        )
    removed = store.prune_anomalies(retention_days=365, max_rows=3)
    assert removed == 4
    recent = store.list_recent(limit=10)
    assert len(recent) == 3
    assert all(item.code in {"code_4", "code_5", "code_6"} for item in recent)


def test_anomaly_store_validates_prune_arguments(tmp_path: Path) -> None:
    store = SQLiteAnomalyStore(db_path=tmp_path / "anomalies.db")
    with pytest.raises(ValueError, match="retention_days"):
        store.prune_anomalies(retention_days=0, max_rows=100)
    with pytest.raises(ValueError, match="max_rows"):
        store.prune_anomalies(retention_days=30, max_rows=0)
