"""SQLite-backed story persistence adapter for local editing workflows."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


@dataclass(frozen=True)
class StoredStory:
    """Canonical story record returned by the persistence adapter."""

    story_id: str
    owner_id: str
    title: str
    body: str
    created_at_utc: str
    updated_at_utc: str


class SQLiteStoryStore:
    """Persist and query story records from a local SQLite database file."""

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
                CREATE TABLE IF NOT EXISTS stories (
                    story_id TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    body TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_stories_owner_updated
                ON stories(owner_id, updated_at_utc DESC)
                """
            )

    def list_stories(self, *, owner_id: str | None = None, limit: int = 100) -> list[StoredStory]:
        """Return recent story records, optionally filtered by owner."""
        with self._connect() as connection:
            if owner_id is None:
                rows = connection.execute(
                    """
                    SELECT story_id, owner_id, title, body, created_at_utc, updated_at_utc
                    FROM stories
                    ORDER BY updated_at_utc DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT story_id, owner_id, title, body, created_at_utc, updated_at_utc
                    FROM stories
                    WHERE owner_id = ?
                    ORDER BY updated_at_utc DESC
                    LIMIT ?
                    """,
                    (owner_id, limit),
                ).fetchall()
        return [self._from_row(row) for row in rows]

    def create_story(self, *, owner_id: str, title: str, body: str) -> StoredStory:
        """Create and persist a story record."""
        now = datetime.now(UTC).isoformat()
        story_id = uuid4().hex
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO stories (story_id, owner_id, title, body, created_at_utc, updated_at_utc)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (story_id, owner_id, title, body, now, now),
            )
        return self.get_story(story_id=story_id) or StoredStory(
            story_id=story_id,
            owner_id=owner_id,
            title=title,
            body=body,
            created_at_utc=now,
            updated_at_utc=now,
        )

    def get_story(self, *, story_id: str) -> StoredStory | None:
        """Load one story by id."""
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT story_id, owner_id, title, body, created_at_utc, updated_at_utc
                FROM stories
                WHERE story_id = ?
                """,
                (story_id,),
            ).fetchone()
        if row is None:
            return None
        return self._from_row(row)

    def update_story(self, *, story_id: str, title: str, body: str) -> StoredStory | None:
        """Update title/body and return the new record when it exists."""
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE stories
                SET title = ?, body = ?, updated_at_utc = ?
                WHERE story_id = ?
                """,
                (title, body, now, story_id),
            )
            updated_rows = cursor.rowcount
        if updated_rows == 0:
            return None
        return self.get_story(story_id=story_id)

    @staticmethod
    def _from_row(row: sqlite3.Row) -> StoredStory:
        return StoredStory(
            story_id=str(row["story_id"]),
            owner_id=str(row["owner_id"]),
            title=str(row["title"]),
            body=str(row["body"]),
            created_at_utc=str(row["created_at_utc"]),
            updated_at_utc=str(row["updated_at_utc"]),
        )
