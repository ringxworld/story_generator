# ADR 0013: Bounded Observability and Anomaly Retention

## Status

Accepted

## Problem

We need richer operational visibility (logging + anomaly breadcrumbs) without
creating unbounded log growth or noisy persistence. Earlier behavior logged to
stdout only and had no durable anomaly channel for analysis/dashboard failures.

## Non-goals

- Introducing external logging infrastructure (Loki/ELK/Cloud logging) in this ADR.
- Adding distributed tracing.
- Storing full request/response payloads in durable logs.

## Decision

Add a bounded observability layer with two paths:

- Rotating runtime logs configured from `story_gen.cli.api`
- SQLite anomaly event persistence for warning/error breadcrumbs

Implemented components:

- `src/story_gen/adapters/observability.py`
  - one-time process logging setup
  - rotating file handler + console handler
- `src/story_gen/adapters/sqlite_anomaly_store.py`
  - append anomaly records
  - list recent anomalies
  - prune by retention days and max row cap
- `src/story_gen/api/app.py`
  - startup pruning (`STORY_GEN_ANOMALY_RETENTION_DAYS`, `STORY_GEN_ANOMALY_MAX_ROWS`)
  - anomaly writes for quality-gate failures and malformed dashboard payloads

## Public API

No new HTTP endpoints are introduced in this ADR.

New runtime environment variables:

- `STORY_GEN_LOG_LEVEL`
- `STORY_GEN_LOG_PATH`
- `STORY_GEN_LOG_MAX_BYTES`
- `STORY_GEN_LOG_BACKUP_COUNT`
- `STORY_GEN_ACCESS_LOG_LEVEL`
- `STORY_GEN_ANOMALY_RETENTION_DAYS`
- `STORY_GEN_ANOMALY_MAX_ROWS`

## Invariants

- Runtime file logs must remain bounded by rotation settings.
- Anomaly rows must remain bounded by retention + cap pruning.
- Anomalies persist only concise metadata, never full raw content payloads.
- API behavior remains owner-scoped and does not expose anomaly internals publicly.

## Test plan

- Unit tests for SQLite anomaly store write/list/prune behavior.
- API tests for:
  - startup pruning invocation
  - quality-gate failure anomaly persistence
  - malformed dashboard payload anomaly persistence
- Full repository quality gate:
  - `uv run pre-commit run --all-files`
  - `uv run pytest`
  - `uv run mypy`
  - `uv run mkdocs build --strict`
