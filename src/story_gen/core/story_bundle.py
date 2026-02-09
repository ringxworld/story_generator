"""Binary bundle format for sharing complete story analysis artifacts."""

from __future__ import annotations

import json
import struct
import zlib
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import cast

from pydantic import BaseModel, ConfigDict, Field

from story_gen.core.language_translation import SegmentAlignment
from story_gen.core.quality_evaluation import EvaluationMetrics
from story_gen.core.story_analysis_pipeline import StoryAnalysisResult
from story_gen.core.story_schema import STORY_STAGE_ORDER, StoryDocument, StoryStage, TimelinePoint
from story_gen.core.theme_arc_tracking import ArcSignal, ConflictShift, EmotionSignal

BUNDLE_SCHEMA_VERSION = "story_bundle.v1"
BUNDLE_MAGIC = b"SGBN"
_FORMAT_VERSION = 1
_HEADER_STRUCT = struct.Struct(">4sBQQ")
_TRAILER_STRUCT = struct.Struct(">32s32s")

_RECORD_STORY_DOCUMENT = "story_document.json"
_RECORD_DASHBOARD = "dashboard_read_model.json"
_RECORD_TIMELINE_ACTUAL = "timeline_actual.json"
_RECORD_TIMELINE_NARRATIVE = "timeline_narrative.json"
_RECORD_ALIGNMENTS = "segment_alignments.json"
_RECORD_ARCS = "arc_signals.json"
_RECORD_CONFLICTS = "conflict_shifts.json"
_RECORD_EMOTIONS = "emotion_signals.json"
_RECORD_EVALUATION = "evaluation_metrics.json"
_RECORD_GRAPH_SVG = "graph.svg"


class StoryBundleError(RuntimeError):
    """Raised when bundle packing/unpacking fails."""


class _BundleModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class BundleRecordManifest(_BundleModel):
    """Manifest entry for one bundle record."""

    name: str = Field(min_length=1, max_length=200)
    media_type: str = Field(min_length=1, max_length=120)
    offset: int = Field(ge=0)
    length: int = Field(ge=0)
    sha256_hex: str = Field(min_length=64, max_length=64)


class StoryBundleManifest(_BundleModel):
    """Bundle manifest carried in the binary envelope."""

    bundle_schema_version: str = BUNDLE_SCHEMA_VERSION
    bundle_format_version: int = _FORMAT_VERSION
    story_id: str = Field(min_length=1)
    story_schema_version: str = Field(min_length=1)
    created_at_utc: str = Field(min_length=1)
    compression: str = "zlib"
    payload_sha256_hex: str = Field(min_length=64, max_length=64)
    records: list[BundleRecordManifest] = Field(min_length=1)


@dataclass(frozen=True)
class UnpackedStoryAnalysisBundle:
    """Structured artifacts restored from an `.sgb` bundle."""

    manifest: StoryBundleManifest
    story_document: StoryDocument
    dashboard_read_model: dict[str, object]
    timeline_actual: list[TimelinePoint]
    timeline_narrative: list[TimelinePoint]
    alignments: list[SegmentAlignment]
    arcs: list[ArcSignal]
    conflicts: list[ConflictShift]
    emotions: list[EmotionSignal]
    evaluation: EvaluationMetrics
    graph_svg: str


@dataclass(frozen=True)
class _RecordPayload:
    name: str
    media_type: str
    content: bytes


def pack_story_analysis_bundle(
    *,
    result: StoryAnalysisResult,
    created_at_utc: str | None = None,
) -> bytes:
    """Encode story analysis artifacts into a compressed binary bundle."""
    timestamp = created_at_utc or datetime.now(UTC).isoformat()
    records = _build_records(result=result)
    payload = b"".join(record.content for record in records)
    payload_sha = sha256(payload).hexdigest()
    record_manifests = _record_manifests(records=records)
    manifest = StoryBundleManifest(
        bundle_schema_version=BUNDLE_SCHEMA_VERSION,
        bundle_format_version=_FORMAT_VERSION,
        story_id=result.document.story_id,
        story_schema_version=result.document.schema_version,
        created_at_utc=timestamp,
        compression="zlib",
        payload_sha256_hex=payload_sha,
        records=record_manifests,
    )
    manifest_bytes = _stable_json_bytes(manifest.model_dump(mode="json"))
    compressed_payload = zlib.compress(payload, level=9)

    header = _HEADER_STRUCT.pack(
        BUNDLE_MAGIC,
        _FORMAT_VERSION,
        len(manifest_bytes),
        len(compressed_payload),
    )
    trailer = _TRAILER_STRUCT.pack(
        sha256(manifest_bytes).digest(),
        sha256(compressed_payload).digest(),
    )
    return b"".join([header, manifest_bytes, compressed_payload, trailer])


def unpack_story_analysis_bundle(bundle_bytes: bytes) -> UnpackedStoryAnalysisBundle:
    """Decode and validate a binary story bundle."""
    if len(bundle_bytes) < _HEADER_STRUCT.size + _TRAILER_STRUCT.size:
        raise StoryBundleError("bundle is too small")

    header = bundle_bytes[: _HEADER_STRUCT.size]
    magic, format_version, manifest_length, payload_length = _HEADER_STRUCT.unpack(header)
    if magic != BUNDLE_MAGIC:
        raise StoryBundleError("invalid bundle magic")
    if format_version != _FORMAT_VERSION:
        raise StoryBundleError(f"unsupported bundle format version: {format_version}")

    expected_size = _HEADER_STRUCT.size + manifest_length + payload_length + _TRAILER_STRUCT.size
    if len(bundle_bytes) != expected_size:
        raise StoryBundleError("bundle length does not match header metadata")

    manifest_start = _HEADER_STRUCT.size
    manifest_end = manifest_start + manifest_length
    payload_end = manifest_end + payload_length

    manifest_bytes = bundle_bytes[manifest_start:manifest_end]
    compressed_payload = bundle_bytes[manifest_end:payload_end]
    trailer_bytes = bundle_bytes[payload_end:]
    manifest_digest, payload_digest = _TRAILER_STRUCT.unpack(trailer_bytes)
    if sha256(manifest_bytes).digest() != manifest_digest:
        raise StoryBundleError("manifest checksum mismatch")
    if sha256(compressed_payload).digest() != payload_digest:
        raise StoryBundleError("compressed payload checksum mismatch")

    try:
        manifest = StoryBundleManifest.model_validate_json(manifest_bytes.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise StoryBundleError("invalid manifest payload") from exc

    if manifest.bundle_schema_version != BUNDLE_SCHEMA_VERSION:
        raise StoryBundleError(
            f"unsupported bundle schema version: {manifest.bundle_schema_version}"
        )
    if manifest.compression != "zlib":
        raise StoryBundleError(f"unsupported compression method: {manifest.compression}")

    try:
        payload = zlib.decompress(compressed_payload)
    except zlib.error as exc:
        raise StoryBundleError("failed to decompress payload") from exc
    if sha256(payload).hexdigest() != manifest.payload_sha256_hex:
        raise StoryBundleError("payload checksum mismatch")

    by_name = _slice_records(payload=payload, manifest=manifest)
    required_records = {
        _RECORD_STORY_DOCUMENT,
        _RECORD_DASHBOARD,
        _RECORD_TIMELINE_ACTUAL,
        _RECORD_TIMELINE_NARRATIVE,
        _RECORD_ALIGNMENTS,
        _RECORD_ARCS,
        _RECORD_CONFLICTS,
        _RECORD_EMOTIONS,
        _RECORD_EVALUATION,
        _RECORD_GRAPH_SVG,
    }
    missing = sorted(record for record in required_records if record not in by_name)
    if missing:
        raise StoryBundleError(f"bundle missing required records: {missing}")

    story_document = StoryDocument.model_validate_json(
        by_name[_RECORD_STORY_DOCUMENT].decode("utf-8")
    )
    dashboard = _decode_json_object(by_name[_RECORD_DASHBOARD])
    timeline_actual = _decode_timeline(by_name[_RECORD_TIMELINE_ACTUAL])
    timeline_narrative = _decode_timeline(by_name[_RECORD_TIMELINE_NARRATIVE])
    alignments = _decode_alignments(by_name[_RECORD_ALIGNMENTS])
    arcs = _decode_arcs(by_name[_RECORD_ARCS])
    conflicts = _decode_conflicts(by_name[_RECORD_CONFLICTS])
    emotions = _decode_emotions(by_name[_RECORD_EMOTIONS])
    evaluation = _decode_evaluation(by_name[_RECORD_EVALUATION])
    graph_svg = by_name[_RECORD_GRAPH_SVG].decode("utf-8")
    return UnpackedStoryAnalysisBundle(
        manifest=manifest,
        story_document=story_document,
        dashboard_read_model=dashboard,
        timeline_actual=timeline_actual,
        timeline_narrative=timeline_narrative,
        alignments=alignments,
        arcs=arcs,
        conflicts=conflicts,
        emotions=emotions,
        evaluation=evaluation,
        graph_svg=graph_svg,
    )


def _build_records(*, result: StoryAnalysisResult) -> list[_RecordPayload]:
    return [
        _RecordPayload(
            name=_RECORD_STORY_DOCUMENT,
            media_type="application/json",
            content=result.document.model_dump_json().encode("utf-8"),
        ),
        _RecordPayload(
            name=_RECORD_DASHBOARD,
            media_type="application/json",
            content=_stable_json_bytes(asdict(result.dashboard)),
        ),
        _RecordPayload(
            name=_RECORD_TIMELINE_ACTUAL,
            media_type="application/json",
            content=_stable_json_bytes(
                [point.model_dump(mode="json") for point in result.timeline.actual_time]
            ),
        ),
        _RecordPayload(
            name=_RECORD_TIMELINE_NARRATIVE,
            media_type="application/json",
            content=_stable_json_bytes(
                [point.model_dump(mode="json") for point in result.timeline.narrative_order]
            ),
        ),
        _RecordPayload(
            name=_RECORD_ALIGNMENTS,
            media_type="application/json",
            content=_stable_json_bytes([asdict(alignment) for alignment in result.alignments]),
        ),
        _RecordPayload(
            name=_RECORD_ARCS,
            media_type="application/json",
            content=_stable_json_bytes([asdict(arc) for arc in result.arcs]),
        ),
        _RecordPayload(
            name=_RECORD_CONFLICTS,
            media_type="application/json",
            content=_stable_json_bytes([asdict(conflict) for conflict in result.conflicts]),
        ),
        _RecordPayload(
            name=_RECORD_EMOTIONS,
            media_type="application/json",
            content=_stable_json_bytes([asdict(emotion) for emotion in result.emotions]),
        ),
        _RecordPayload(
            name=_RECORD_EVALUATION,
            media_type="application/json",
            content=_stable_json_bytes(asdict(result.evaluation)),
        ),
        _RecordPayload(
            name=_RECORD_GRAPH_SVG,
            media_type="image/svg+xml",
            content=result.graph_svg.encode("utf-8"),
        ),
    ]


def _record_manifests(*, records: list[_RecordPayload]) -> list[BundleRecordManifest]:
    offset = 0
    manifests: list[BundleRecordManifest] = []
    for record in records:
        length = len(record.content)
        manifests.append(
            BundleRecordManifest(
                name=record.name,
                media_type=record.media_type,
                offset=offset,
                length=length,
                sha256_hex=sha256(record.content).hexdigest(),
            )
        )
        offset += length
    return manifests


def _slice_records(*, payload: bytes, manifest: StoryBundleManifest) -> dict[str, bytes]:
    records: dict[str, bytes] = {}
    next_expected_offset = 0
    for record in manifest.records:
        if record.offset != next_expected_offset:
            raise StoryBundleError("record offsets are not contiguous")
        end = record.offset + record.length
        if end > len(payload):
            raise StoryBundleError(f"record '{record.name}' exceeds payload bounds")
        content = payload[record.offset : end]
        if sha256(content).hexdigest() != record.sha256_hex:
            raise StoryBundleError(f"record checksum mismatch for '{record.name}'")
        records[record.name] = content
        next_expected_offset = end
    if next_expected_offset != len(payload):
        raise StoryBundleError("record table does not consume full payload")
    return records


def _decode_json_object(data: bytes) -> dict[str, object]:
    parsed = json.loads(data.decode("utf-8"))
    if not isinstance(parsed, dict):
        raise StoryBundleError("dashboard payload must be a JSON object")
    return parsed


def _decode_timeline(data: bytes) -> list[TimelinePoint]:
    parsed = json.loads(data.decode("utf-8"))
    if not isinstance(parsed, list):
        raise StoryBundleError("timeline payload must be a JSON array")
    return [TimelinePoint.model_validate(item) for item in parsed]


def _decode_alignments(data: bytes) -> list[SegmentAlignment]:
    parsed = json.loads(data.decode("utf-8"))
    if not isinstance(parsed, list):
        raise StoryBundleError("alignments payload must be a JSON array")
    return [
        SegmentAlignment(
            source_segment_id=str(item["source_segment_id"]),
            source_offsets=tuple(item["source_offsets"]),
            target_offsets=tuple(item["target_offsets"]),
            method=str(item["method"]),
            quality_score=float(item["quality_score"]),
        )
        for item in parsed
    ]


def _decode_arcs(data: bytes) -> list[ArcSignal]:
    parsed = json.loads(data.decode("utf-8"))
    if not isinstance(parsed, list):
        raise StoryBundleError("arcs payload must be a JSON array")
    return [
        ArcSignal(
            entity_id=str(item["entity_id"]),
            entity_name=str(item["entity_name"]),
            stage=_parse_story_stage(item["stage"]),
            state=str(item["state"]),
            delta=float(item["delta"]),
            evidence_segment_ids=_parse_segment_ids(item.get("evidence_segment_ids")),
            provenance_segment_ids=_parse_segment_ids(
                item.get("provenance_segment_ids", item.get("evidence_segment_ids"))
            ),
            confidence=float(item.get("confidence", 0.0)),
        )
        for item in parsed
    ]


def _decode_conflicts(data: bytes) -> list[ConflictShift]:
    parsed = json.loads(data.decode("utf-8"))
    if not isinstance(parsed, list):
        raise StoryBundleError("conflicts payload must be a JSON array")
    return [
        ConflictShift(
            stage=_parse_story_stage(item["stage"]),
            from_state=_parse_story_stage(item["from_state"]),
            to_state=_parse_story_stage(item["to_state"]),
            intensity_delta=float(item["intensity_delta"]),
            evidence_segment_ids=_parse_segment_ids(item.get("evidence_segment_ids")),
            provenance_segment_ids=_parse_segment_ids(
                item.get("provenance_segment_ids", item.get("evidence_segment_ids"))
            ),
            confidence=float(item.get("confidence", 0.0)),
        )
        for item in parsed
    ]


def _decode_emotions(data: bytes) -> list[EmotionSignal]:
    parsed = json.loads(data.decode("utf-8"))
    if not isinstance(parsed, list):
        raise StoryBundleError("emotions payload must be a JSON array")
    return [
        EmotionSignal(
            stage=_parse_story_stage(item["stage"]),
            tone=str(item["tone"]),
            score=float(item["score"]),
            evidence_segment_ids=_parse_segment_ids(item.get("evidence_segment_ids")),
            provenance_segment_ids=_parse_segment_ids(
                item.get("provenance_segment_ids", item.get("evidence_segment_ids"))
            ),
            confidence=float(item.get("confidence", 0.0)),
        )
        for item in parsed
    ]


def _decode_evaluation(data: bytes) -> EvaluationMetrics:
    parsed = json.loads(data.decode("utf-8"))
    if not isinstance(parsed, dict):
        raise StoryBundleError("evaluation payload must be a JSON object")
    return EvaluationMetrics(
        confidence_floor=float(parsed["confidence_floor"]),
        hallucination_risk=float(parsed["hallucination_risk"]),
        translation_quality=float(parsed["translation_quality"]),
        timeline_consistency=float(parsed.get("timeline_consistency", 1.0)),
    )


def _stable_json_bytes(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def _parse_story_stage(raw: object) -> StoryStage:
    stage = str(raw).strip().lower()
    if stage not in STORY_STAGE_ORDER:
        raise StoryBundleError(f"invalid story stage value: {raw}")
    return cast(StoryStage, stage)


def _parse_segment_ids(raw: object) -> tuple[str, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise StoryBundleError("segment id payload must be a JSON array")
    return tuple(str(item) for item in raw)
