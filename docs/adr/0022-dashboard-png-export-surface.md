# ADR 0021: Dashboard PNG Export Surface

## Status

Accepted

## Problem

Dashboard graph exports existed only as SVG text payloads. Teams that need static
image artifacts for docs, reports, and snapshots need a deterministic PNG export
path that works offline and does not add heavy rendering dependencies.

## Non-goals

- Replacing current dashboard graph contracts or graph layout strategy.
- Adding third-party rasterization services or browser-based renderers.
- Expanding this ADR to timeline/heatmap image rendering.

## Decision

- Add deterministic PNG rendering in `story_gen.core.dashboard_views`.
- Expose API endpoint:
  - `GET /api/v1/stories/{story_id}/dashboard/graph/export.png`
- Expose CLI command:
  - `story-dashboard-export --format {svg|png}`
- Keep existing SVG export endpoint unchanged for backward compatibility.

## Public API

New API response model:

- `DashboardGraphPngExportResponse`
  - `format`: `"png"`
  - `png_base64`: base64-encoded PNG payload

New CLI entrypoint:

- `story-dashboard-export`
  - owner-scoped export from SQLite latest analysis run
  - supports `--format svg` and `--format png`

## Invariants

- PNG generation is deterministic for the same graph nodes/edges.
- Existing SVG export route and response shape remain unchanged.
- Owner isolation remains enforced for API and CLI export paths.
- No new runtime dependency is introduced for raster export.

## Test plan

- Core pipeline test verifies PNG bytes are deterministic and have PNG signature.
- API tests verify PNG export route shape and deterministic payload.
- CLI tests verify SVG/PNG write behavior and owner-mismatch failure path.
