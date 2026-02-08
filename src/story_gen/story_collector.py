"""Compatibility re-export for story collector script internals.

The script implementation lives in `story_gen.cli.story_collector`.
"""

from __future__ import annotations

from story_gen.cli import story_collector as _script

__all__ = [name for name in dir(_script) if not name.startswith("__")]
globals().update({name: getattr(_script, name) for name in __all__})
