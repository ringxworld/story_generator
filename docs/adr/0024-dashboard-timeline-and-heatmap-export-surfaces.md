# ADR 0024: Dashboard Timeline and Heatmap Export Surfaces

## Status

Accepted

## Problem

Dashboard image export support only covered graph projections. Teams also need
deterministic timeline and theme-heatmap image artifacts for reporting and
documentation workflows, with parity across API and CLI surfaces.

## Non-goals

- Replacing current timeline or heatmap read-model contracts.
- Introducing third-party rendering engines.
- Changing owner-scoping or authentication semantics of dashboard endpoints.

## Decision

- Add deterministic timeline and theme-heatmap renderers in
  `story_gen.core.dashboard_views` for both SVG and PNG.
- Expose API endpoints:
  - `GET /api/v1/stories/{story_id}/dashboard/timeline/export.svg`
  - `GET /api/v1/stories/{story_id}/dashboard/timeline/export.png`
  - `GET /api/v1/stories/{story_id}/dashboard/themes/heatmap/export.svg`
  - `GET /api/v1/stories/{story_id}/dashboard/themes/heatmap/export.png`
- Extend CLI export surface:
  - `story-dashboard-export --view {graph|timeline|theme-heatmap} --format {svg|png}`
- Keep existing graph export routes and payload shape unchanged.

## Public API

New response usage:

- `DashboardSvgExportResponse`
  - `format`: `"svg"`
  - `svg`: deterministic SVG payload
- `DashboardPngExportResponse`
  - `format`: `"png"`
  - `png_base64`: deterministic PNG payload

New API routes provide timeline and theme-heatmap exports with these models.

CLI behavior:

- `story-dashboard-export` now supports `--view`:
  - `graph` (default)
  - `timeline`
  - `theme-heatmap`

## Invariants

- Same input dashboard payload produces byte-identical PNG and text-identical
  SVG exports per view.
- Export routes remain owner-scoped and require an existing analysis run.
- Missing or malformed dashboard payload segments fail loudly rather than
  silently producing partial output.
- No new runtime dependencies are introduced for rendering.

## Test plan

- Core tests verify deterministic timeline and heatmap SVG/PNG exports.
- API tests verify new endpoint availability, output shape, determinism, owner
  isolation, and malformed payload failures.
- CLI tests verify timeline/heatmap SVG+PNG write behavior, determinism, and
  failure behavior on missing payload sections.
