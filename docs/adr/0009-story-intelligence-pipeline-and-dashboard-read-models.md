# ADR 0009: Story Intelligence Pipeline and Dashboard Read Models

## Status

Accepted

## Problem

We need an end-to-end deterministic pipeline that turns story text into:

- extracted events and beats
- themes/arcs/conflict/emotion signals
- timeline views (actual-time + narrative-order)
- macro/meso/micro insights
- quality-gated dashboard read models

We also need stable API endpoints for interactive graph/timeline dashboard views
and export-ready SVG output.

## Non-goals

- Replacing SQLite with a managed datastore in this ADR.
- Integrating external LLM translation providers in this ADR.
- Introducing a new backend runtime outside FastAPI.

## Decision

Add a canonical `story_analysis.v1` core schema and deterministic internal stages:

- ingestion/chunk normalization
- language detection + translation fallback
- event/entity extraction
- narrative beat detection
- theme/arc/conflict/emotion tracking
- timeline composition
- insight generation (macro/meso/micro)
- confidence and quality gate checks

Persist complete analysis runs in SQLite through a dedicated adapter:

- `adapters/sqlite_story_analysis_store.py`

Expose analysis and dashboard read models via new authenticated API routes:

- `/api/v1/stories/{story_id}/analysis/*`
- `/api/v1/stories/{story_id}/dashboard/*`

Expose an interactive graph payload and SVG export endpoint.

## Public API

New request/response contracts:

- `StoryAnalysisRunRequest`
- `StoryAnalysisRunResponse`
- dashboard response models for overview, timeline, heatmap, arcs, drilldown, graph, and SVG export

New endpoints:

- `POST /api/v1/stories/{story_id}/analysis/run`
- `GET /api/v1/stories/{story_id}/analysis/latest`
- `GET /api/v1/stories/{story_id}/dashboard/overview`
- `GET /api/v1/stories/{story_id}/dashboard/timeline`
- `GET /api/v1/stories/{story_id}/dashboard/themes/heatmap`
- `GET /api/v1/stories/{story_id}/dashboard/arcs`
- `GET /api/v1/stories/{story_id}/dashboard/drilldown/{item_id}`
- `GET /api/v1/stories/{story_id}/dashboard/graph`
- `GET /api/v1/stories/{story_id}/dashboard/graph/export.svg`

## Invariants

- `story_analysis.v1` remains the canonical schema key.
- All derived artifacts include confidence and provenance.
- Pipeline ordering is deterministic for identical inputs.
- Dashboard endpoints are owner-scoped and require authentication.
- Quality gate values are persisted with each analysis run before dashboard exposure.

## Test plan

- core unit tests for ingestion/translation/contracts and pipeline determinism
- adapter tests for analysis persistence and schema mismatch failure
- API tests for analysis lifecycle, dashboard reads, and owner isolation
- frontend tests for analysis run trigger and graph/dashboard rendering

## Update 2026-02-09 (Issue #6)

### Problem

Theme and arc outputs were stage-aware but too shallow for explainability. We needed
stronger per-stage evidence, trend direction tracking, and confidence metadata that
can power dashboard drilldown without breaking existing heatmap and arc chart clients.

### Non-goals

- Introducing external model providers in this update.
- Changing dashboard heatmap or arc endpoint response shapes.

### Public API

- Keep `DashboardThemeHeatmapCellResponse` shape stable: `theme`, `stage`, `intensity`.
- Keep `DashboardArcPointResponse` shape stable: `lane`, `stage`, `value`, `label`.
- Expand drilldown coverage to include theme, arc, conflict, and emotion items in
  addition to insight items.

### Invariants

- Theme signals must include evidence IDs and provenance source segment IDs with overlap.
- Theme signal confidence must be positive.
- Arc/conflict/emotion records must carry evidence, provenance segment references, and confidence when generated.
- Bundle decoding must stay backward compatible with older arc/conflict/emotion payloads.

### Test plan

- Add stage-regression tests that verify theme strengthening/fading transitions.
- Validate arc/conflict/emotion outputs include explainability fields.
- Validate dashboard drilldown includes theme/arc/conflict/emotion entries.
- Validate bundle roundtrip preserves new fields and still decodes old-compatible payloads.
