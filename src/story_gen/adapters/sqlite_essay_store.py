"""SQLite-backed persistence for essay-mode workspaces."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


@dataclass(frozen=True)
class StoredEssay:
    """Stored essay-mode workspace."""

    essay_id: str
    owner_id: str
    title: str
    blueprint_json: str
    draft_text: str
    created_at_utc: str
    updated_at_utc: str


class SQLiteEssayStore:
    """Persist and query essay workspaces from one SQLite database."""

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
                CREATE TABLE IF NOT EXISTS essays (
                    essay_id TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    blueprint_json TEXT NOT NULL,
                    draft_text TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL,
                    FOREIGN KEY (owner_id) REFERENCES users(user_id)
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_essays_owner_updated
                ON essays(owner_id, updated_at_utc DESC)
                """
            )

    def list_essays(self, *, owner_id: str, limit: int = 100) -> list[StoredEssay]:
        """Return recent essays for one owner."""
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT essay_id, owner_id, title, blueprint_json, draft_text, created_at_utc, updated_at_utc
                FROM essays
                WHERE owner_id = ?
                ORDER BY updated_at_utc DESC
                LIMIT ?
                """,
                (owner_id, limit),
            ).fetchall()
        return [self._essay_from_row(row) for row in rows]

    def create_essay(
        self,
        *,
        owner_id: str,
        title: str,
        blueprint_json: str,
        draft_text: str,
    ) -> StoredEssay:
        """Create one essay workspace."""
        now = datetime.now(UTC).isoformat()
        essay_id = uuid4().hex
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO essays (essay_id, owner_id, title, blueprint_json, draft_text, created_at_utc, updated_at_utc)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (essay_id, owner_id, title, blueprint_json, draft_text, now, now),
            )
        created = self.get_essay(essay_id=essay_id)
        if created is None:
            raise RuntimeError("Created essay could not be loaded.")
        return created

    def get_essay(self, *, essay_id: str) -> StoredEssay | None:
        """Load one essay by id."""
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT essay_id, owner_id, title, blueprint_json, draft_text, created_at_utc, updated_at_utc
                FROM essays
                WHERE essay_id = ?
                """,
                (essay_id,),
            ).fetchone()
        if row is None:
            return None
        return self._essay_from_row(row)

    def update_essay(
        self,
        *,
        essay_id: str,
        title: str,
        blueprint_json: str,
        draft_text: str,
    ) -> StoredEssay | None:
        """Update one essay workspace."""
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE essays
                SET title = ?, blueprint_json = ?, draft_text = ?, updated_at_utc = ?
                WHERE essay_id = ?
                """,
                (title, blueprint_json, draft_text, now, essay_id),
            )
            updated_rows = cursor.rowcount
        if updated_rows == 0:
            return None
        return self.get_essay(essay_id=essay_id)

    @staticmethod
    def _essay_from_row(row: sqlite3.Row) -> StoredEssay:
        return StoredEssay(
            essay_id=str(row["essay_id"]),
            owner_id=str(row["owner_id"]),
            title=str(row["title"]),
            blueprint_json=str(row["blueprint_json"]),
            draft_text=str(row["draft_text"]),
            created_at_utc=str(row["created_at_utc"]),
            updated_at_utc=str(row["updated_at_utc"]),
        )
