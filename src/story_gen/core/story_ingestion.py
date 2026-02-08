"""Deterministic ingestion and chunking for story analysis."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from hashlib import sha256
from typing import Literal, cast

from story_gen.core.story_schema import RawSegment, stable_id

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_WHITESPACE = re.compile(r"[ \t]+")
_PARA_BREAK = re.compile(r"\n{3,}")


@dataclass(frozen=True)
class IngestionRequest:
    """Ingestion payload accepted by the analysis pipeline."""

    source_type: str
    source_text: str
    idempotency_key: str


SourceType = Literal["text", "document", "transcript"]


@dataclass(frozen=True)
class IngestionArtifact:
    """Normalized artifact emitted by ingestion stage."""

    source_hash: str
    normalized_text: str
    dedupe_key: str
    segments: list[RawSegment]


def normalize_text(text: str) -> str:
    """Normalize text while preserving paragraph boundaries."""
    normalized = unicodedata.normalize("NFKC", text.replace("\r\n", "\n"))
    normalized = _CONTROL_CHARS.sub("", normalized)
    lines = [_WHITESPACE.sub(" ", line).strip() for line in normalized.split("\n")]
    normalized = "\n".join(lines)
    normalized = _PARA_BREAK.sub("\n\n", normalized)
    normalized = "\n".join(line for line in normalized.split("\n") if line or line == "")
    return normalized.strip()


def _chunk_text(text: str, *, chunk_chars: int = 900, overlap: int = 120) -> list[str]:
    if chunk_chars <= overlap:
        raise ValueError("chunk_chars must be greater than overlap.")
    if len(text) <= chunk_chars:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        stop = min(len(text), start + chunk_chars)
        window = text[start:stop]
        if stop < len(text):
            split_at = window.rfind("\n\n")
            if split_at > chunk_chars // 3:
                stop = start + split_at
                window = text[start:stop]
        piece = window.strip()
        if piece:
            chunks.append(piece)
        if stop >= len(text):
            break
        start = max(stop - overlap, start + 1)
    return chunks


def ingest_story_text(request: IngestionRequest) -> IngestionArtifact:
    """Create deterministic segment artifacts from one raw source string."""
    normalized = normalize_text(request.source_text)
    if not normalized:
        raise ValueError("source_text must contain non-empty content after normalization.")

    source_hash = sha256(normalized.encode("utf-8")).hexdigest()
    dedupe_key = sha256(f"{request.idempotency_key}|{source_hash}".encode("utf-8")).hexdigest()

    source_type: SourceType = (
        cast(SourceType, request.source_type)
        if request.source_type in {"text", "document", "transcript"}
        else "text"
    )

    segments: list[RawSegment] = []
    char_cursor = 0
    for index, chunk in enumerate(_chunk_text(normalized), start=1):
        segment_id = stable_id(prefix="seg", text=f"{source_hash}:{index}")
        start = char_cursor
        end = start + len(chunk)
        segments.append(
            RawSegment(
                segment_id=segment_id,
                source_type=source_type,
                original_text=chunk,
                normalized_text=chunk,
                translated_text=None,
                segment_index=index,
                char_start=start,
                char_end=end,
            )
        )
        char_cursor = end + 1

    return IngestionArtifact(
        source_hash=source_hash,
        normalized_text=normalized,
        dedupe_key=dedupe_key,
        segments=segments,
    )
