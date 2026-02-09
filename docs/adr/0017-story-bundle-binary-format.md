# ADR 0017: Story Bundle Binary Format

## Status

Accepted

## Problem

Story analysis artifacts are currently exchanged as separate JSON payloads.
That is easy to inspect but inefficient for sharing full analysis sessions
(document, timeline, themes, arcs, confidence data, and graph export).

We need one portable bundle artifact with strong integrity checks and stable
versioning, without adding external runtime dependencies.

## Non-goals

- Replacing database persistence with bundle files.
- Encrypting bundle payloads in v1.
- Backward compatibility across major bundle schema versions.

## Decision

Introduce a custom `.sgb` binary container (`story_bundle.v1`) with:

- fixed header (`magic`, `format_version`, manifest length, payload length)
- UTF-8 JSON manifest describing records and offsets
- zlib-compressed payload block containing concatenated artifact records
- fixed trailer with SHA-256 digests for manifest and compressed payload
- per-record SHA-256 checksums in manifest

## Public API

Python core surface:

- `pack_story_analysis_bundle(...) -> bytes`
- `unpack_story_analysis_bundle(...) -> UnpackedStoryAnalysisBundle`

File extension for shared artifacts:

- `.sgb`

## Invariants

- Bundle magic remains `SGBN`.
- Manifest and payload checksums are validated before decode.
- Record offsets are contiguous and fully consume payload.
- `story_analysis.v1` content remains unchanged inside record payloads.

## Test plan

- Round-trip bundle encode/decode for real analysis output.
- Deterministic bytes for fixed input + fixed timestamp.
- Failure tests for invalid magic and corrupted payload digest.
- Full repository quality gates remain green.
