"""Typed contracts shared by API handlers and Python interfaces."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field, model_validator


class ThemeBlock(BaseModel):
    """Theme unit used in blueprint-driven story planning."""

    key: str = Field(min_length=1, max_length=120)
    statement: str = Field(min_length=1, max_length=1000)
    priority: int = Field(default=1, ge=1, le=10)


class CharacterBlock(BaseModel):
    """Character unit used in blueprint-driven story planning."""

    key: str = Field(min_length=1, max_length=120)
    role: str = Field(min_length=1, max_length=200)
    motivation: str = Field(min_length=1, max_length=2000)
    voice_markers: list[str] = Field(default_factory=list)
    relationships: dict[str, str] = Field(default_factory=dict)


class ChapterBlock(BaseModel):
    """Chapter unit that captures ordering and narrative dependencies."""

    key: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=300)
    objective: str = Field(min_length=1, max_length=3000)
    required_themes: list[str] = Field(default_factory=list)
    participating_characters: list[str] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list)
    draft_text: str | None = None


class StoryBlueprint(BaseModel):
    """Portable story contract users can edit via web or Python."""

    premise: str = Field(min_length=1, max_length=4000)
    themes: list[ThemeBlock] = Field(default_factory=list)
    characters: list[CharacterBlock] = Field(default_factory=list)
    chapters: list[ChapterBlock] = Field(default_factory=list)
    canon_rules: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_unique_keys(self) -> StoryBlueprint:
        def keys_are_unique(values: list[str]) -> bool:
            return len(values) == len(set(values))

        if not keys_are_unique([theme.key for theme in self.themes]):
            raise ValueError("Theme keys must be unique.")
        if not keys_are_unique([character.key for character in self.characters]):
            raise ValueError("Character keys must be unique.")
        if not keys_are_unique([chapter.key for chapter in self.chapters]):
            raise ValueError("Chapter keys must be unique.")
        return self


class StoryCreateRequest(BaseModel):
    """Create one story workspace for the authenticated user."""

    title: str = Field(min_length=1, max_length=300)
    blueprint: StoryBlueprint


class StoryUpdateRequest(BaseModel):
    """Update title and blueprint for an existing story workspace."""

    title: str = Field(min_length=1, max_length=300)
    blueprint: StoryBlueprint


class StoryResponse(BaseModel):
    """Story payload returned by the API."""

    story_id: str
    owner_id: str
    title: str
    blueprint: StoryBlueprint
    created_at_utc: str
    updated_at_utc: str


class AuthRegisterRequest(BaseModel):
    """Register a user account for local/dev story editing."""

    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=8, max_length=200)
    display_name: str = Field(min_length=1, max_length=120)


class AuthLoginRequest(BaseModel):
    """Authenticate and request an access token."""

    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=8, max_length=200)


class AuthTokenResponse(BaseModel):
    """Bearer token payload used by web and Python clients."""

    access_token: str
    token_type: str = "bearer"
    expires_at_utc: str


class UserResponse(BaseModel):
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
