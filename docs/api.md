# API

The HTTP API provides authenticated local-preview story editing backed by SQLite.

## Run locally

```bash
uv run story-api --host 127.0.0.1 --port 8000 --reload
```

Choose a custom DB path:

```bash
uv run story-api --db-path work/local/story_gen.db
```

## Endpoints

- `GET /healthz`
  - Returns service health payload.
- `GET /api/v1`
  - Returns API stage metadata and endpoint list.
- `POST /api/v1/auth/register`
  - Registers a local user account.
- `POST /api/v1/auth/login`
  - Returns bearer token for subsequent requests.
- `GET /api/v1/me`
  - Returns authenticated user profile.
- `GET /api/v1/stories?limit=<n>`
  - Lists stories for the authenticated owner.
- `POST /api/v1/stories`
  - Creates one story blueprint for authenticated owner.
- `GET /api/v1/stories/{story_id}`
  - Reads one owner-scoped story.
- `PUT /api/v1/stories/{story_id}`
  - Updates title/blueprint for one owner-scoped story.
- `POST /api/v1/stories/{story_id}/features/extract`
  - Runs story-first chapter feature extraction and persists a new run.
- `GET /api/v1/stories/{story_id}/features/latest`
  - Returns latest persisted extraction result for that story.
- `POST /api/v1/stories/{story_id}/analysis/run`
  - Runs deterministic story intelligence analysis (ingestion, translation, beats, themes, timeline, insights).
- `GET /api/v1/stories/{story_id}/analysis/latest`
  - Returns latest persisted analysis run summary for that story.
- `GET /api/v1/stories/{story_id}/dashboard/overview`
  - Returns big-picture card payload for dashboard.
- `GET /api/v1/stories/{story_id}/dashboard/v1/overview`
  - Versioned alias of dashboard overview payload for frontend contract pinning.
- `GET /api/v1/stories/{story_id}/dashboard/timeline`
  - Returns timeline lane payloads for actual-time and narrative-order views.
- `GET /api/v1/stories/{story_id}/dashboard/v1/timeline`
  - Versioned alias of timeline lane payloads.
- `GET /api/v1/stories/{story_id}/dashboard/timeline/export.svg`
  - Returns deterministic SVG export payload for timeline lanes.
- `GET /api/v1/stories/{story_id}/dashboard/timeline/export.png`
  - Returns deterministic PNG export payload (`png_base64`) for timeline lanes.
- `GET /api/v1/stories/{story_id}/dashboard/themes/heatmap`
  - Returns theme-by-stage intensity cells.
- `GET /api/v1/stories/{story_id}/dashboard/v1/themes/heatmap`
  - Versioned alias of theme heatmap payload.
- `GET /api/v1/stories/{story_id}/dashboard/themes/heatmap/export.svg`
  - Returns deterministic SVG export payload for theme heatmaps.
- `GET /api/v1/stories/{story_id}/dashboard/themes/heatmap/export.png`
  - Returns deterministic PNG export payload (`png_base64`) for theme heatmaps.
- `GET /api/v1/stories/{story_id}/dashboard/arcs`
  - Returns arc chart points (character/conflict/emotion lanes).
- `GET /api/v1/stories/{story_id}/dashboard/drilldown/{item_id}`
  - Returns detail payload for one drilldown item.
- `GET /api/v1/stories/{story_id}/dashboard/graph`
  - Returns graph nodes/edges for interactive rendering.
- `GET /api/v1/stories/{story_id}/dashboard/graph/export.svg`
  - Returns SVG export payload for graph image use.
- `GET /api/v1/stories/{story_id}/dashboard/graph/export.png`
  - Returns deterministic PNG export payload (`png_base64`) for graph image use.
- `GET /api/v1/essays?limit=<n>`
  - Lists essays for the authenticated owner.
- `POST /api/v1/essays`
  - Creates one essay workspace with `EssayBlueprint` and optional draft text.
- `GET /api/v1/essays/{essay_id}`
  - Reads one owner-scoped essay.
- `PUT /api/v1/essays/{essay_id}`
  - Updates title/blueprint/draft for one owner-scoped essay.
- `POST /api/v1/essays/{essay_id}/evaluate`
  - Runs deterministic quality checks for "good essay mode" and returns pass/fail findings.

## Interactive API docs (Swagger)

When the API is running locally:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`

## Hosted Python API reference (Pages)

Static module reference pages are published to:

- `https://ringxworld.github.io/story_generator/pydoc/`

These pages are generated from Python source via `pdoc` during the Pages deploy workflow.

## Dashboard Drilldown Payload Shape

`GET /api/v1/stories/{story_id}/dashboard/drilldown/{item_id}` returns:

- `item_id`: stable drilldown item key (for example `theme:<theme_id>`).
- `item_type`: one of `insight:*`, `theme`, `arc`, `conflict`, `emotion`.
- `title`: short display title for panel header.
- `content`: narrative detail text for selected item.
- `evidence_segment_ids`: ordered segment ids backing the drilldown claim.

Auth flow in Swagger UI:

1. Call `POST /api/v1/auth/login`.
2. Copy `access_token` from the response.
3. Click **Authorize** in Swagger UI and paste `Bearer <token>`.
4. Execute authenticated routes (`/stories/*`, `/essays/*`).

## Notes

- OpenAPI docs are available at `/docs` when running locally.
- Default local DB path is `work/local/story_gen.db`.
- Auth is bearer-token based for local/dev workflows.
- Dashboard and analysis endpoints are owner-scoped and require a prior analysis run.
- This API is intended for local/dev now and backend hosting later.
- GitHub Pages is static hosting only, so it can serve docs/front-end but not this Python API.
- Python users can work with the same contracts via `story_gen.api` and `story-blueprint`.
- Override allowed CORS origins with `STORY_GEN_CORS_ORIGINS` (comma-separated).

## Dashboard export CLI

Export the latest owner-scoped dashboard graph from SQLite:

```bash
uv run story-dashboard-export \
  --db-path work/local/story_gen.db \
  --story-id <story-id> \
  --owner-id <owner-id> \
  --view timeline \
  --format png \
  --output work/exports/<story-id>-timeline.png
```
