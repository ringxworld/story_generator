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
