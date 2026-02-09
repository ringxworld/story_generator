from __future__ import annotations

import struct

import pytest

from story_gen.core.story_analysis_pipeline import run_story_analysis
from story_gen.core.story_bundle import (
    BUNDLE_MAGIC,
    StoryBundleError,
    pack_story_analysis_bundle,
    unpack_story_analysis_bundle,
)


def _sample_story() -> str:
    return (
        "Rhea enters the archive and finds her family's ledger. "
        "A conflict erupts when the council denies the records. "
        "She confronts the council in the central hall. "
        "The city accepts the truth and begins to heal."
    )


def test_story_bundle_roundtrip_restores_analysis_artifacts() -> None:
    result = run_story_analysis(story_id="story-bundle-1", source_text=_sample_story())
    bundle_bytes = pack_story_analysis_bundle(
        result=result,
        created_at_utc="2026-02-09T00:00:00+00:00",
    )
    unpacked = unpack_story_analysis_bundle(bundle_bytes)
    assert unpacked.manifest.bundle_schema_version == "story_bundle.v1"
    assert unpacked.story_document.story_id == "story-bundle-1"
    assert unpacked.dashboard_read_model["overview"]
    assert len(unpacked.timeline_actual) == len(result.timeline.actual_time)
    assert len(unpacked.timeline_narrative) == len(result.timeline.narrative_order)
    assert len(unpacked.alignments) == len(result.alignments)
    assert unpacked.graph_svg.startswith("<svg")


def test_story_bundle_is_deterministic_with_fixed_timestamp() -> None:
    result = run_story_analysis(story_id="story-bundle-2", source_text=_sample_story())
    first = pack_story_analysis_bundle(result=result, created_at_utc="2026-02-09T00:00:00+00:00")
    second = pack_story_analysis_bundle(result=result, created_at_utc="2026-02-09T00:00:00+00:00")
    assert first == second


def test_story_bundle_rejects_invalid_magic() -> None:
    result = run_story_analysis(story_id="story-bundle-3", source_text=_sample_story())
    bundle_bytes = bytearray(pack_story_analysis_bundle(result=result))
    bundle_bytes[:4] = b"XXXX"
    with pytest.raises(StoryBundleError, match="invalid bundle magic"):
        unpack_story_analysis_bundle(bytes(bundle_bytes))


def test_story_bundle_rejects_corrupted_payload_digest() -> None:
    result = run_story_analysis(story_id="story-bundle-4", source_text=_sample_story())
    bundle_bytes = bytearray(pack_story_analysis_bundle(result=result))
    header = bytes(bundle_bytes[:21])
    _, _, manifest_length, payload_length = struct.unpack(">4sBQQ", header)
    payload_start = 21 + manifest_length
    payload_end = payload_start + payload_length
    bundle_bytes[payload_end - 1] ^= 0x01
    with pytest.raises(StoryBundleError, match="compressed payload checksum mismatch"):
        unpack_story_analysis_bundle(bytes(bundle_bytes))


def test_story_bundle_magic_constant_is_stable() -> None:
    assert BUNDLE_MAGIC == b"SGBN"
