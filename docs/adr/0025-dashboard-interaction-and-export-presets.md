# ADR 0025: Dashboard Interaction and Export Presets

## Status

Accepted

## Problem

The dashboard baseline rendered read models, but analysts could not efficiently filter graph context, inspect node-specific drilldown evidence, or generate repeatable export bundles across graph, timeline, and theme heatmap views.

## Non-goals

- Replace the existing dashboard read model schemas.
- Introduce server-side graph filtering APIs.
- Change auth/session architecture or story analysis pipeline contracts.

## Decision

Implement a client-driven interaction layer on top of existing dashboard endpoints:

- Add graph filters for stage, node group, theme, entity, relation, and label text.
- Add keyboard graph navigation and keyboard-selectable graph nodes.
- Add drilldown panel resolution for selected nodes via existing drilldown endpoint with node-type-aware candidate IDs.
- Add export preset generation in the web UI for graph, timeline, and theme heatmap in SVG and PNG.
- Keep offline demo behavior representative of production interaction patterns.

Update graph construction and export rendering to support analyst legibility:

- Replace dense theme-to-beat linking with evidence/stage-aware linking.
- Add arc-to-beat `drives` relations from stage/evidence alignment.
- Include a visual legend in graph SVG and PNG exports.

## Public API

- No new backend endpoints were introduced.
- Existing endpoints now receive broader usage:
  - `GET /api/v1/stories/{story_id}/dashboard/drilldown/{item_id}`
  - `GET /api/v1/stories/{story_id}/dashboard/graph/export.svg`
  - `GET /api/v1/stories/{story_id}/dashboard/graph/export.png`
  - `GET /api/v1/stories/{story_id}/dashboard/timeline/export.svg`
  - `GET /api/v1/stories/{story_id}/dashboard/timeline/export.png`
  - `GET /api/v1/stories/{story_id}/dashboard/themes/heatmap/export.svg`
  - `GET /api/v1/stories/{story_id}/dashboard/themes/heatmap/export.png`

## Invariants

- Module boundaries from `tools/check_imports.py` remain enforced.
- Graph export layout remains deterministic for a stable input graph.
- Dashboard filters are view-only; they do not mutate source read models.
- Offline demo remains functional and preserves representative interaction parity.

## Test Plan

- `npm run --prefix web typecheck`
- `npm run --prefix web test`
- `uv lock --check`
- `uv run python tools/check_imports.py`
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run mypy`
- `uv run pytest`
- `uv run mkdocs build --strict`

## Consequences

- Improved analyst workflow and accessibility for dashboard graph exploration.
- Increased UI state complexity from combined filtering, drilldown, and export presets.
- Graph edge density is reduced and better aligned to evidence/stage semantics, which may alter previously assumed edge counts in downstream visual analysis.
