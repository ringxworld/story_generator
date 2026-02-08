"""SQLite-backed persistence for users, tokens, and story blueprints."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


@dataclass(frozen=True)
class StoredUser:
    """Stored user account data."""

    user_id: str
    email: str
    display_name: str
    password_hash: str
    created_at_utc: str


@dataclass(frozen=True)
class StoredToken:
    """Stored bearer-token session."""

    token_id: str
    user_id: str
    token_value: str
    expires_at_utc: str
    created_at_utc: str


@dataclass(frozen=True)
class StoredStory:
    """Stored story workspace data."""

    story_id: str
    owner_id: str
    title: str
    blueprint_json: str
    created_at_utc: str
    updated_at_utc: str


class SQLiteStoryStore:
    """Persist and query story platform records from one SQLite database."""

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
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    display_name TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS access_tokens (
                    token_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    token_value TEXT NOT NULL UNIQUE,
                    expires_at_utc TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS stories (
                    story_id TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    blueprint_json TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL,
                    FOREIGN KEY (owner_id) REFERENCES users(user_id)
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_stories_owner_updated
                ON stories(owner_id, updated_at_utc DESC)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_tokens_user
                ON access_tokens(user_id, expires_at_utc DESC)
                """
            )

    def create_user(
        self, *, email: str, display_name: str, password_hash: str
    ) -> StoredUser | None:
        """Create a user record; return None when email is already taken."""
        now = datetime.now(UTC).isoformat()
        user_id = uuid4().hex
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO users (user_id, email, display_name, password_hash, created_at_utc)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (user_id, email.lower(), display_name, password_hash, now),
                )
        except sqlite3.IntegrityError:
            return None
        return self.get_user_by_id(user_id=user_id)

    def get_user_by_email(self, *, email: str) -> StoredUser | None:
        """Load one user by normalized email."""
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT user_id, email, display_name, password_hash, created_at_utc
                FROM users
                WHERE email = ?
                """,
                (email.lower(),),
            ).fetchone()
        if row is None:
            return None
        return self._user_from_row(row)

    def get_user_by_id(self, *, user_id: str) -> StoredUser | None:
        """Load one user by id."""
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT user_id, email, display_name, password_hash, created_at_utc
                FROM users
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
        if row is None:
            return None
        return self._user_from_row(row)

    def create_token(self, *, user_id: str, token_value: str, expires_at_utc: str) -> StoredToken:
        """Create and store a bearer token."""
        token_id = uuid4().hex
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO access_tokens (token_id, user_id, token_value, expires_at_utc, created_at_utc)
                VALUES (?, ?, ?, ?, ?)
                """,
                (token_id, user_id, token_value, expires_at_utc, now),
            )
        return StoredToken(
            token_id=token_id,
            user_id=user_id,
            token_value=token_value,
            expires_at_utc=expires_at_utc,
            created_at_utc=now,
        )

    def get_user_by_token(self, *, token_value: str, now_utc: str) -> StoredUser | None:
        """Resolve a bearer token into a user if it is still valid."""
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT u.user_id, u.email, u.display_name, u.password_hash, u.created_at_utc
                FROM access_tokens t
                JOIN users u ON u.user_id = t.user_id
                WHERE t.token_value = ? AND t.expires_at_utc > ?
                """,
                (token_value, now_utc),
            ).fetchone()
        if row is None:
            return None
        return self._user_from_row(row)

    def list_stories(self, *, owner_id: str, limit: int = 100) -> list[StoredStory]:
        """Return recent stories for one owner."""
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT story_id, owner_id, title, blueprint_json, created_at_utc, updated_at_utc
                FROM stories
                WHERE owner_id = ?
                ORDER BY updated_at_utc DESC
                LIMIT ?
                """,
                (owner_id, limit),
            ).fetchall()
        return [self._story_from_row(row) for row in rows]

    def create_story(self, *, owner_id: str, title: str, blueprint_json: str) -> StoredStory:
        """Create and persist one story workspace."""
        now = datetime.now(UTC).isoformat()
        story_id = uuid4().hex
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO stories (story_id, owner_id, title, blueprint_json, created_at_utc, updated_at_utc)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (story_id, owner_id, title, blueprint_json, now, now),
            )
        story = self.get_story(story_id=story_id)
        if story is None:
            raise RuntimeError("Created story could not be loaded.")
        return story

    def get_story(self, *, story_id: str) -> StoredStory | None:
        """Load one story by id."""
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT story_id, owner_id, title, blueprint_json, created_at_utc, updated_at_utc
                FROM stories
                WHERE story_id = ?
                """,
                (story_id,),
            ).fetchone()
        if row is None:
            return None
        return self._story_from_row(row)

    def update_story(self, *, story_id: str, title: str, blueprint_json: str) -> StoredStory | None:
        """Update title/blueprint and return the new stored value."""
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE stories
                SET title = ?, blueprint_json = ?, updated_at_utc = ?
                WHERE story_id = ?
                """,
                (title, blueprint_json, now, story_id),
            )
            updated_rows = cursor.rowcount
        if updated_rows == 0:
            return None
        return self.get_story(story_id=story_id)

    @staticmethod
    def _user_from_row(row: sqlite3.Row) -> StoredUser:
        return StoredUser(
            user_id=str(row["user_id"]),
            email=str(row["email"]),
            display_name=str(row["display_name"]),
            password_hash=str(row["password_hash"]),
            created_at_utc=str(row["created_at_utc"]),
        )

    @staticmethod
    def _story_from_row(row: sqlite3.Row) -> StoredStory:
        return StoredStory(
            story_id=str(row["story_id"]),
            owner_id=str(row["owner_id"]),
            title=str(row["title"]),
            blueprint_json=str(row["blueprint_json"]),
            created_at_utc=str(row["created_at_utc"]),
            updated_at_utc=str(row["updated_at_utc"]),
        )
