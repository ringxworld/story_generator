# ADR 0027: Pipeline Ingestion Resilience and Canary Enforcement

## Status

Accepted

## Problem

Pipeline execution relied on plain-text ingestion assumptions and lacked a
single deterministic canary command that proves stage-by-stage health in CI.
Timeline outputs also lacked explicit conflict diagnostics and consistency
signals in quality gating, which made chronology regressions harder to detect.
After initial rollout, canary coverage still skewed to one mostly English
transcript path, leaving multilingual and non-transcript regressions under-
represented in CI.

## Non-goals

- Replacing existing extraction, beat, or theme algorithms.
- Introducing external queue infrastructure for ingestion retries.
- Changing authentication/ownership semantics for story routes.

## Decision

- Expand ingestion adaptation to support `text`, `document`, and `transcript`
  source types with deterministic normalization and issue capture.
- Persist ingestion jobs in SQLite with idempotent dedupe semantics, retry
  counters, and explicit status transitions.
- Expose ingestion polling status on API routes used by dashboard clients.
- Add a strict pipeline canary CLI command and enforce it in CI and pre-push
  checks.
- Extend canary execution to a fixture-driven variant matrix that includes
  multilingual and code-switching transcript paths plus at least one
  non-transcript source-type path.
- Upgrade timeline composition to include dual-view diagnostics and a
  consistency score consumed by the quality gate.

## Public API

New or updated public surfaces:

- API:
  - `POST /api/v1/stories/{story_id}/analysis/run`
    - accepts optional `idempotency_key`.
  - `GET /api/v1/stories/{story_id}/ingestion/status`
    - returns `IngestionStatusResponse`.
- Contract registry:
  - `story.ingestion.status`.
- CLI:
  - `story-pipeline-canary` entrypoint.
    - supports variant matrix mode via fixture file and JSON summary output.
  - `make pipeline-canary`.

## Invariants

- Same normalized content + idempotency key yields a stable dedupe key.
- Retry attempts do not create duplicate ingestion job rows for the same
  owner/story/dedupe tuple.
- Ingestion status transitions are explicit: `processing -> succeeded|failed`.
- Timeline projections expose deterministic narrative and chronological views.
- Timeline conflicts are surfaced with stable conflict IDs and codes.
- Quality gate decisions include timeline consistency.
- Canary output is structured JSON and stage-specific on failure.
- Matrix canary output contains per-variant stage diagnostics, key metrics,
  and explicit failing stage/error payloads when regressions occur.

## Test plan

- Unit tests for ingestion adapters, retry/dedupe store semantics, and timeline
  conflict/consistency behavior.
- API tests for ingestion polling endpoint, owner isolation, idempotent reruns,
  warning surfacing, and persistence-failure status transitions.
- CLI tests for pipeline canary success output.
- CLI tests for variant matrix mode and summary output persistence.
- Contract-registry snapshot checks include ingestion status contract.
- CI executes strict matrix canary after full pytest and uploads canary summary
  artifact.
