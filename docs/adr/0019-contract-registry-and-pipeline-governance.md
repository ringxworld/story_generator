# ADR 0019: Contract Registry and Pipeline Governance

## Status

Accepted

## Problem

Schema and pipeline contracts are spread across API models, core schema models,
pipeline validator functions, and docs. As scope expands, this creates drift risk:

- contract changes are not always discoverable in one place
- stage boundary assumptions can change without explicit tracking
- reviewers lack a single artifact that proves what contracts exist now

## Non-goals

- Replacing pydantic models with a new schema framework.
- Generating API server routes from the registry.
- Enforcing backward compatibility for every future major version.

## Public API

Tracking surfaces introduced:

- `src/story_gen/api/contract_registry.py`
  - builds `ContractRegistrySnapshot`
- `tools/export_contract_registry.py`
  - exports `work/contracts/story_pipeline_contract_registry.v1.json`
- `src/story_gen/core/pipeline_contracts.py`
  - exposes tracked stage contracts via `registered_pipeline_stage_contracts()`

Developer command:

- `make contracts-export`

## Invariants

- Registry version remains explicit (`contract_registry.v1`).
- Canonical story schema version stays explicit (`story_analysis.v1`).
- Each contract entry has a unique stable ID.
- Each pipeline stage entry has a unique stable stage ID.
- Exported registry JSON must match runtime snapshot in tests.
- Story analysis orchestration validates input/output stage contracts at runtime.

## Version Migration Policy

- Backward-compatible additions stay within `story_analysis.v1`.
- Breaking schema changes require a new explicit key (for example `story_analysis.v2`).
- Storage adapters fail fast when persisted schema version does not match expected version.
- Registry/docs must declare both old and new versions during migration windows.

## Test plan

- Add unit tests for runtime registry content and uniqueness.
- Add equality test between runtime snapshot and exported registry JSON.
- Keep story analysis pipeline tests green with runtime validators enabled.
- Run pre-commit and repository quality gates before merge.
