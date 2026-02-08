"""Compatibility re-export for reference pipeline script internals.

The script implementation lives in `story_gen.cli.reference_pipeline`.
"""

from __future__ import annotations

from story_gen.cli import reference_pipeline as _script

__all__ = [name for name in dir(_script) if not name.startswith("__")]
globals().update({name: getattr(_script, name) for name in __all__})
