# ADR 0016: Native Feature Metrics Acceleration Path

## Status

Accepted

## Problem

Chapter-level feature extraction currently computes sentence/token/dialogue metrics
in Python. That is deterministic, but it will become a throughput bottleneck as
story corpora and chapter sizes grow.

We need an incremental C++ adoption path that improves CPU-bound text metric
passes without changing the end-to-end pipeline architecture.

## Non-goals

- Rewriting the full story pipeline in C++.
- Introducing compiled Python extension dependencies in `core`.
- Changing persisted feature schema or API response contracts.

## Decision

Introduce a native executable for chapter metric computation and expose it through
`src/story_gen/native/` as an opt-in engine.

- Add `story_feature_metrics` C++ tool in `cpp/`.
- Keep Python feature extraction as the default behavior.
- Add a CLI engine selector (`python` or `native`) for `story-features`.
- Route native integration through the `native` boundary only.

## Public API

CLI behavior change:

- `story-features` adds `--engine` with values:
  - `python` (default)
  - `native`

No REST API contract changes.
No schema version changes for `story_features.v1`.

## Invariants

- `story_features.v1` output shape remains stable.
- Native execution failures do not silently corrupt outputs.
- `core` does not import `native` modules.
- Native path remains optional and explicit.

## Test plan

- Unit tests for native wrapper parsing and failure handling.
- CLI tests for engine selection path.
- Existing feature extraction tests continue passing for default Python engine.
- Build and smoke test native executable via existing CMake targets.
