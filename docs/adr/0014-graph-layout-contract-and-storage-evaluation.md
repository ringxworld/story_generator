# ADR 0014: Graph Layout Contract and Storage Evaluation

## Status

Accepted

## Problem

The dashboard graph needs deeper interactive insight while remaining stable for
API consumers and low-friction local development. We also need a clear storage
strategy as graph complexity grows.

## Non-goals

- Migrating to a managed graph database in this ADR.
- Replacing the current dashboard frontend stack in this ADR.
- Introducing 3D graph rendering for alpha.

## Decision

1. Extend the dashboard graph node contract with deterministic layout hints:
   - `layout_x`
   - `layout_y`
2. Keep graph edge/node extraction deterministic in core pipeline outputs.
3. Keep SQLite as the default persistence backend for alpha.
4. Document evaluation outcomes for visualization and storage options
   (`docs/graph_strategy.md`) to guide future migrations.

## Public API

Updated response model:

- `DashboardGraphNodeResponse`
  - adds optional `layout_x` and `layout_y`

Behavior:

- New analysis runs populate graph layout hints.
- Existing persisted analysis payloads remain readable because layout fields are optional.

## Invariants

- Graph payload remains owner-scoped and auth-protected.
- Layout generation is deterministic for identical input artifacts.
- API compatibility is preserved for old stored dashboard payloads.
- Storage remains local-first and migration-ready through adapters.

## Test plan

- Core pipeline test verifies graph nodes include layout coordinates.
- API test verifies `/dashboard/graph` returns layout fields for new runs.
- Frontend tests/typecheck continue to pass with optional coordinate fallback.
