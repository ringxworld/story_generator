"""SQLite anomaly sink for durable warning/error breadcrumbs."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4


@dataclass(frozen=True)
class StoredAnomaly:
    """Persisted anomaly metadata."""

    anomaly_id: str
    created_at_utc: str
    scope: str
    code: str
    severity: str
    message: str
    metadata_json: str


class SQLiteAnomalyStore:
    """Append-only anomaly records with retention and capacity pruning."""

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
                CREATE TABLE IF NOT EXISTS anomaly_events (
                    anomaly_id TEXT PRIMARY KEY,
                    created_at_utc TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    code TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_anomaly_events_created
                ON anomaly_events(created_at_utc DESC)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_anomaly_events_scope_code
                ON anomaly_events(scope, code, created_at_utc DESC)
                """
            )

    def write_anomaly(
        self,
        *,
        scope: str,
        code: str,
        severity: str,
        message: str,
        metadata: dict[str, object] | None = None,
    ) -> StoredAnomaly:
        """Persist one anomaly event."""
        anomaly_id = uuid4().hex
        created_at_utc = datetime.now(UTC).isoformat()
        payload = json.dumps(metadata or {}, ensure_ascii=False, sort_keys=True)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO anomaly_events (
                    anomaly_id,
                    created_at_utc,
                    scope,
                    code,
                    severity,
                    message,
                    metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (anomaly_id, created_at_utc, scope, code, severity, message, payload),
            )
        return StoredAnomaly(
            anomaly_id=anomaly_id,
            created_at_utc=created_at_utc,
            scope=scope,
            code=code,
            severity=severity,
            message=message,
            metadata_json=payload,
        )

    def prune_anomalies(self, *, retention_days: int, max_rows: int) -> int:
        """Delete old records and keep total rows under max_rows."""
        if retention_days <= 0:
            raise ValueError("retention_days must be positive.")
        if max_rows <= 0:
            raise ValueError("max_rows must be positive.")

        cutoff = datetime.now(UTC) - timedelta(days=retention_days)
        removed = 0
        with self._connect() as connection:
            deleted = connection.execute(
                """
                DELETE FROM anomaly_events
                WHERE created_at_utc < ?
                """,
                (cutoff.isoformat(),),
            )
            removed += int(deleted.rowcount)

            total = connection.execute("SELECT COUNT(*) AS total FROM anomaly_events").fetchone()
            assert total is not None
            total_rows = int(total["total"])
            overflow = max(0, total_rows - max_rows)
            if overflow > 0:
                deleted_overflow = connection.execute(
                    """
                    DELETE FROM anomaly_events
                    WHERE anomaly_id IN (
                        SELECT anomaly_id
                        FROM anomaly_events
                        ORDER BY created_at_utc ASC
                        LIMIT ?
                    )
                    """,
                    (overflow,),
                )
                removed += int(deleted_overflow.rowcount)
        return removed

    def list_recent(self, *, limit: int = 100) -> list[StoredAnomaly]:
        """Fetch recent anomaly records."""
        if limit <= 0:
            raise ValueError("limit must be positive.")
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    anomaly_id,
                    created_at_utc,
                    scope,
                    code,
                    severity,
                    message,
                    metadata_json
                FROM anomaly_events
                ORDER BY created_at_utc DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            StoredAnomaly(
                anomaly_id=str(row["anomaly_id"]),
                created_at_utc=str(row["created_at_utc"]),
                scope=str(row["scope"]),
                code=str(row["code"]),
                severity=str(row["severity"]),
                message=str(row["message"]),
                metadata_json=str(row["metadata_json"]),
            )
            for row in rows
        ]
