# ADR 0006: Story-First Feature Extraction and Schema Enforcement

## Status

Accepted

## Problem

We need a robust "start from story, then extract features" pipeline with
predictable schemas so downstream generation controls and evaluations stay
stable over time.

## Non-goals

- Full semantic NLP stack rollout in this ADR.
- Production analytics warehouse design.
- Replacing existing story CRUD contracts.

## Decision

Introduce a deterministic chapter feature extraction pipeline:

- core extraction logic in `core/story_feature_pipeline.py`
- persistence adapter in `adapters/sqlite_feature_store.py`
- API endpoints for extraction and latest run retrieval

Adopt explicit schema/version enforcement:

- pydantic contract strict mode (`extra="forbid"`)
- schema constant `story_features.v1`
- table-level version registry (`feature_schema_versions`)
- fail-fast on schema mismatch

## Public API

New endpoints:

- `POST /api/v1/stories/{story_id}/features/extract`
- `GET /api/v1/stories/{story_id}/features/latest`

New CLI:

- `story-features`

## Invariants

- extraction starts from persisted story blueprint chapters
- feature run is owner-scoped and story-scoped
- schema version mismatch blocks writes/reads until migrated

## Test plan

- unit tests for core extraction behavior
- adapter tests for persistence and schema mismatch failures
- API tests for extraction lifecycle and owner isolation
- contract tests for docs/entrypoints updates
