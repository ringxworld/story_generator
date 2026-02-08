"""Public API surface for HTTP serving and Python-first interfaces."""

from story_gen.api.app import create_app
from story_gen.api.contracts import (
    EssayBlueprint,
    StoryBlueprint,
    load_blueprint_json,
    load_essay_blueprint_json,
    save_blueprint_json,
    save_essay_blueprint_json,
)
from story_gen.api.python_interface import AuthSession, StoryApiClient

__all__ = [
    "AuthSession",
    "EssayBlueprint",
    "StoryApiClient",
    "StoryBlueprint",
    "create_app",
    "load_blueprint_json",
    "load_essay_blueprint_json",
    "save_blueprint_json",
    "save_essay_blueprint_json",
]
