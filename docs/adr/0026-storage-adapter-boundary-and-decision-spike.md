# ADR 0026: Storage Adapter Boundary and Decision Spike

## Status

Accepted

## Problem

The project needs a credible path from local SQLite JSON persistence to optional
document/graph-oriented backends without changing API contracts. We also need
measured guidance for when graph-oriented storage is worth its operational cost.

## Non-goals

- Production rollout of managed MongoDB or graph database infrastructure.
- Rewriting story CRUD stores away from SQLite in this ADR.
- API contract or endpoint shape changes for dashboard/analysis consumers.

## Decision

1. Introduce a storage adapter boundary for analysis persistence:
   - `StoryAnalysisStorePort` protocol
   - `create_story_analysis_store(...)` factory
2. Keep SQLite as default backend for local/dev correctness and lowest ops cost.
3. Add prototype adapters behind explicit feature flags:
   - `mongo-prototype`: append-only JSONL document model
   - `graph-prototype`: append-only JSONL + adjacency sidecar index
4. Add benchmark tooling to compare representative query latency for
   Mongo-style document traversal vs graph-indexed traversal.
5. Add a storage decision matrix and operations runbook (backup, restore,
   retention, rollback) so backend switching stays operationally safe.

## Public API

- No HTTP endpoint or response schema changes.
- New runtime configuration (internal):
  - `STORY_GEN_ANALYSIS_BACKEND`:
    `sqlite` | `mongo-prototype` | `graph-prototype`
  - `STORY_GEN_ENABLE_MONGO_ADAPTER` (`1` to enable prototype)
  - `STORY_GEN_ENABLE_GRAPH_ADAPTER` (`1` to enable prototype)

## Invariants

- Canonical API contracts remain source of truth independent of backend.
- Latest analysis read semantics stay owner/story scoped and deterministic.
- SQLite remains the safe default when no backend is configured.
- Prototype adapters must not bypass schema version enforcement.

## Test Plan

- Add unit tests for adapter factory feature-flag gating.
- Add parity tests for Mongo/graph prototype round-trip read/write behavior.
- Run benchmark tooling and publish measured results in docs.
- Run full repository quality gates and strict docs build.

## Consequences

- Backend experimentation can proceed without API churn.
- Prototype adapters add configuration complexity and operational caveats.
- Feature-flag removal plan:
  - Keep prototype flags during evaluation under issues
    https://github.com/ringxworld/story_generator/issues/97 and
    https://github.com/ringxworld/story_generator/issues/11.
  - Remove flags after a production backend decision is accepted and rollout
    runbooks are validated in CI and staging.
