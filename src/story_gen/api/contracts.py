"""Typed contracts shared by API handlers and Python interfaces."""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator

KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{0,119}$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ContractModel(BaseModel):
    """Base model config used by all API contracts."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def _normalize_key(value: str, *, field_name: str) -> str:
    normalized = value.strip().lower()
    if not KEY_PATTERN.match(normalized):
        raise ValueError(
            f"{field_name} must match `{KEY_PATTERN.pattern}` (lowercase, digits, _ or -, starts with a-z)."
        )
    return normalized


def _dedupe_ordered(values: Iterable[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = value.strip().lower()
        if not normalized:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped


class ThemeBlock(ContractModel):
    """Theme unit used in blueprint-driven story planning."""

    key: str = Field(min_length=1, max_length=120)
    statement: str = Field(min_length=1, max_length=1000)
    priority: int = Field(default=1, ge=1, le=10)

    @field_validator("key")
    @classmethod
    def _validate_key(cls, value: str) -> str:
        return _normalize_key(value, field_name="Theme key")


class CharacterBlock(ContractModel):
    """Character unit used in blueprint-driven story planning."""

    key: str = Field(min_length=1, max_length=120)
    role: str = Field(min_length=1, max_length=200)
    motivation: str = Field(min_length=1, max_length=2000)
    voice_markers: list[str] = Field(default_factory=list)
    relationships: dict[str, str] = Field(default_factory=dict)

    @field_validator("key")
    @classmethod
    def _validate_key(cls, value: str) -> str:
        return _normalize_key(value, field_name="Character key")

    @field_validator("voice_markers")
    @classmethod
    def _normalize_voice_markers(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values if value.strip()]
        return list(dict.fromkeys(normalized))

    @field_validator("relationships")
    @classmethod
    def _normalize_relationship_keys(cls, values: dict[str, str]) -> dict[str, str]:
        normalized: dict[str, str] = {}
        for key, value in values.items():
            normalized_key = _normalize_key(str(key), field_name="Relationship key")
            if not str(value).strip():
                raise ValueError("Relationship values must be non-empty strings.")
            normalized[normalized_key] = str(value).strip()
        return normalized


class ChapterBlock(ContractModel):
    """Chapter unit that captures ordering and narrative dependencies."""

    key: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=300)
    objective: str = Field(min_length=1, max_length=3000)
    required_themes: list[str] = Field(default_factory=list)
    participating_characters: list[str] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list)
    draft_text: str | None = None

    @field_validator("key")
    @classmethod
    def _validate_key(cls, value: str) -> str:
        return _normalize_key(value, field_name="Chapter key")

    @field_validator("required_themes", "participating_characters", "prerequisites")
    @classmethod
    def _normalize_key_lists(cls, values: list[str]) -> list[str]:
        return _dedupe_ordered(values)


class StoryBlueprint(ContractModel):
    """Portable story contract users can edit via web or Python."""

    premise: str = Field(min_length=1, max_length=4000)
    themes: list[ThemeBlock] = Field(default_factory=list)
    characters: list[CharacterBlock] = Field(default_factory=list)
    chapters: list[ChapterBlock] = Field(default_factory=list)
    canon_rules: list[str] = Field(default_factory=list)

    @field_validator("canon_rules")
    @classmethod
    def _normalize_canon_rules(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values if value.strip()]
        return list(dict.fromkeys(normalized))

    @model_validator(mode="after")
    def _validate_invariants(self) -> StoryBlueprint:
        def keys_are_unique(values: list[str]) -> bool:
            return len(values) == len(set(values))

        if not self.premise.strip():
            raise ValueError("Premise must not be empty.")
        if not keys_are_unique([theme.key for theme in self.themes]):
            raise ValueError("Theme keys must be unique.")
        if not keys_are_unique([character.key for character in self.characters]):
            raise ValueError("Character keys must be unique.")
        if not keys_are_unique([chapter.key for chapter in self.chapters]):
            raise ValueError("Chapter keys must be unique.")

        theme_keys = {theme.key for theme in self.themes}
        character_keys = {character.key for character in self.characters}
        chapter_keys = {chapter.key for chapter in self.chapters}

        for chapter in self.chapters:
            unknown_themes = [key for key in chapter.required_themes if key not in theme_keys]
            if unknown_themes:
                raise ValueError(
                    f"Chapter '{chapter.key}' references unknown theme keys: {unknown_themes}."
                )
            unknown_characters = [
                key for key in chapter.participating_characters if key not in character_keys
            ]
            if unknown_characters:
                raise ValueError(
                    f"Chapter '{chapter.key}' references unknown character keys: {unknown_characters}."
                )
            unknown_prerequisites = [key for key in chapter.prerequisites if key not in chapter_keys]
            if unknown_prerequisites:
                raise ValueError(
                    f"Chapter '{chapter.key}' references unknown prerequisite chapter keys: {unknown_prerequisites}."
                )
            if chapter.key in chapter.prerequisites:
                raise ValueError(f"Chapter '{chapter.key}' cannot depend on itself.")

        for character in self.characters:
            dangling_relationships = [
                key for key in character.relationships.keys() if key not in character_keys
            ]
            if dangling_relationships:
                raise ValueError(
                    f"Character '{character.key}' has relationships to unknown characters: {dangling_relationships}."
                )

        graph: dict[str, set[str]] = {
            chapter.key: set(chapter.prerequisites) for chapter in self.chapters
        }
        if _has_cycle(graph):
            raise ValueError("Chapter prerequisites contain a dependency cycle.")
        return self


def _has_cycle(graph: dict[str, set[str]]) -> bool:
    temporary: set[str] = set()
    permanent: set[str] = set()

    def visit(node: str) -> bool:
        if node in permanent:
            return False
        if node in temporary:
            return True
        temporary.add(node)
        for dependency in graph.get(node, set()):
            if dependency in graph and visit(dependency):
                return True
        temporary.remove(node)
        permanent.add(node)
        return False

    return any(visit(node) for node in graph if node not in permanent)


class StoryCreateRequest(ContractModel):
    """Create one story workspace for the authenticated user."""

    title: str = Field(min_length=1, max_length=300)
    blueprint: StoryBlueprint


class StoryUpdateRequest(ContractModel):
    """Update title and blueprint for an existing story workspace."""

    title: str = Field(min_length=1, max_length=300)
    blueprint: StoryBlueprint


class StoryResponse(ContractModel):
    """Story payload returned by the API."""

    story_id: str
    owner_id: str
    title: str
    blueprint: StoryBlueprint
    created_at_utc: str
    updated_at_utc: str


class AuthRegisterRequest(ContractModel):
    """Register a user account for local/dev story editing."""

    email: str = Field(min_length=5, max_length=320)
    password: SecretStr = Field(min_length=8, max_length=200)
    display_name: str = Field(min_length=1, max_length=120)

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not EMAIL_PATTERN.match(normalized):
            raise ValueError("Email must be a valid address.")
        return normalized

    @field_validator("password")
    @classmethod
    def _validate_password(cls, value: SecretStr) -> SecretStr:
        raw = value.get_secret_value()
        if raw.strip() != raw:
            raise ValueError("Password must not start or end with whitespace.")
        if not any(char.isalpha() for char in raw) or not any(char.isdigit() for char in raw):
            raise ValueError("Password must include at least one letter and one number.")
        return value


class AuthLoginRequest(ContractModel):
    """Authenticate and request an access token."""

    email: str = Field(min_length=5, max_length=320)
    password: SecretStr = Field(min_length=8, max_length=200)

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not EMAIL_PATTERN.match(normalized):
            raise ValueError("Email must be a valid address.")
        return normalized


class AuthTokenResponse(ContractModel):
    """Bearer token payload used by web and Python clients."""

    access_token: str
    token_type: str = Field(default="bearer", pattern=r"^bearer$")
    expires_at_utc: str


class UserResponse(ContractModel):
    """Public user profile returned from authenticated endpoints."""

    user_id: str
    email: str
    display_name: str
    created_at_utc: str


def save_blueprint_json(path: Path, blueprint: StoryBlueprint) -> None:
    """Persist blueprint as readable JSON for Python-first workflows."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(blueprint.model_dump_json(indent=2) + "\n", encoding="utf-8")


def load_blueprint_json(path: Path) -> StoryBlueprint:
    """Load and validate blueprint JSON from disk."""
    return StoryBlueprint.model_validate_json(path.read_text(encoding="utf-8"))
