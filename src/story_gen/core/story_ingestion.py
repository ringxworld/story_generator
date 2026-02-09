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
_DOC_PREFIX = re.compile(r"^\s*(?:[#>*-]+|\d+[.)])\s+")
_TRANSCRIPT_STAMP_PREFIX = re.compile(r"^\[(?P<stamp>[0-9:\-. ]{2,32})\]\s*(?P<rest>.*)$")
_TRANSCRIPT_SPEAKER_PREFIX = re.compile(r"^(?P<speaker>[A-Za-z][\w .-]{0,40}):\s*(?P<content>.*)$")
_HAS_ALNUM = re.compile(r"[A-Za-z0-9]")


@dataclass(frozen=True)
class IngestionRequest:
    """Ingestion payload accepted by the analysis pipeline."""

    source_type: str
    source_text: str
    idempotency_key: str
    retry_count: int = 0


SourceType = Literal["text", "document", "transcript"]


@dataclass(frozen=True)
class IngestionIssue:
    """Recoverable ingestion issue captured during source adaptation."""

    code: str
    severity: Literal["warning", "error"]
    message: str
    line_index: int | None = None


@dataclass(frozen=True)
class IngestionMetrics:
    """Counters describing ingestion adaptation/chunking behavior."""

    input_chars: int
    normalized_chars: int
    segment_count: int
    malformed_items: int


@dataclass(frozen=True)
class IngestionArtifact:
    """Normalized artifact emitted by ingestion stage."""

    source_hash: str
    normalized_text: str
    dedupe_key: str
    segments: list[RawSegment]
    source_type: SourceType
    idempotency_key: str
    retry_count: int
    issues: list[IngestionIssue]
    metrics: IngestionMetrics


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


def _adapt_document_source(text: str) -> tuple[str, list[IngestionIssue]]:
    lines: list[str] = []
    for raw in text.replace("\f", "\n\n").split("\n"):
        cleaned = _DOC_PREFIX.sub("", raw).strip()
        lines.append(cleaned)
    adapted = normalize_text("\n".join(lines))
    return adapted, []


def _adapt_transcript_source(text: str) -> tuple[str, list[IngestionIssue]]:
    issues: list[IngestionIssue] = []
    lines: list[str] = []
    for index, raw in enumerate(text.splitlines(), start=1):
        stripped = raw.strip()
        if not stripped:
            continue
        stamp = ""
        speaker = ""
        content = stripped
        stamp_match = _TRANSCRIPT_STAMP_PREFIX.match(content)
        if stamp_match:
            stamp = (stamp_match.group("stamp") or "").strip()
            content = (stamp_match.group("rest") or "").strip()
        if not content:
            issues.append(
                IngestionIssue(
                    code="transcript_line_empty_content",
                    severity="warning",
                    message="Transcript line had no content and was skipped.",
                    line_index=index,
                )
            )
            continue

        speaker_match = _TRANSCRIPT_SPEAKER_PREFIX.match(content)
        if speaker_match:
            speaker = (speaker_match.group("speaker") or "").strip()
            content = (speaker_match.group("content") or "").strip()
        if not content:
            issues.append(
                IngestionIssue(
                    code="transcript_line_empty_content",
                    severity="warning",
                    message="Transcript line had no content and was skipped.",
                    line_index=index,
                )
            )
            continue
        if _HAS_ALNUM.search(content) is None:
            issues.append(
                IngestionIssue(
                    code="transcript_line_unparsed",
                    severity="warning",
                    message="Transcript line could not be parsed and was skipped.",
                    line_index=index,
                )
            )
            continue
        if speaker and stamp:
            normalized_line = f"{speaker} ({stamp}): {content}"
        elif speaker:
            normalized_line = f"{speaker}: {content}"
        elif stamp:
            normalized_line = f"[{stamp}] {content}"
        else:
            normalized_line = content
        lines.append(normalized_line)
    adapted = normalize_text("\n".join(lines))
    if not adapted:
        issues.append(
            IngestionIssue(
                code="transcript_no_usable_lines",
                severity="error",
                message="Transcript did not produce usable normalized content.",
                line_index=None,
            )
        )
    return adapted, issues


def _adapt_source(*, source_type: SourceType, source_text: str) -> tuple[str, list[IngestionIssue]]:
    if source_type == "text":
        return normalize_text(source_text), []
    if source_type == "document":
        return _adapt_document_source(source_text)
    return _adapt_transcript_source(source_text)


def ingest_story_text(request: IngestionRequest) -> IngestionArtifact:
    """Create deterministic segment artifacts from one raw source string."""
    source_type: SourceType = (
        cast(SourceType, request.source_type)
        if request.source_type in {"text", "document", "transcript"}
        else "text"
    )
    issues: list[IngestionIssue] = []
    if request.source_type not in {"text", "document", "transcript"}:
        issues.append(
            IngestionIssue(
                code="source_type_unsupported",
                severity="warning",
                message=f"Unsupported source_type '{request.source_type}', falling back to 'text'.",
            )
        )
    normalized, adapted_issues = _adapt_source(
        source_type=source_type, source_text=request.source_text
    )
    issues.extend(adapted_issues)
    if not normalized:
        raise ValueError("source_text must contain non-empty content after normalization.")

    source_hash = sha256(normalized.encode("utf-8")).hexdigest()
    dedupe_key = sha256(f"{request.idempotency_key}|{source_hash}".encode("utf-8")).hexdigest()

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

    malformed_items = sum(1 for issue in issues if issue.severity in {"warning", "error"})
    return IngestionArtifact(
        source_hash=source_hash,
        normalized_text=normalized,
        dedupe_key=dedupe_key,
        segments=segments,
        source_type=source_type,
        idempotency_key=request.idempotency_key,
        retry_count=max(0, request.retry_count),
        issues=issues,
        metrics=IngestionMetrics(
            input_chars=len(request.source_text),
            normalized_chars=len(normalized),
            segment_count=len(segments),
            malformed_items=malformed_items,
        ),
    )
