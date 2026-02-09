"""Runtime logging configuration with bounded retention."""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

_CONFIGURED = False


def _int_env(name: str, default: int, *, minimum: int, maximum: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(minimum, min(maximum, value))


def configure_runtime_logging() -> None:
    """Configure console + rotating file logs once per process."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    level_name = os.environ.get("STORY_GEN_LOG_LEVEL", "INFO").strip().upper() or "INFO"
    level = getattr(logging, level_name, logging.INFO)
    log_path = Path(
        os.environ.get("STORY_GEN_LOG_PATH", "work/logs/story_gen.log").strip()
        or "work/logs/story_gen.log"
    )
    max_bytes = _int_env(
        "STORY_GEN_LOG_MAX_BYTES", 5 * 1024 * 1024, minimum=64 * 1024, maximum=100 * 1024 * 1024
    )
    backup_count = _int_env("STORY_GEN_LOG_BACKUP_COUNT", 10, minimum=1, maximum=120)

    log_path.parent.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        filename=log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(stream_handler)
    root.addHandler(file_handler)

    access_level_name = os.environ.get("STORY_GEN_ACCESS_LOG_LEVEL", "WARNING").strip().upper()
    access_level = getattr(logging, access_level_name, logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(access_level)

    _CONFIGURED = True
