# ADR 0030: OpenAPI Snapshot and Hosted API Reference

## Status

Accepted

## Problem

The repository exposed live Swagger/ReDoc only when FastAPI was running locally.
Hosted docs on GitHub Pages did not provide a schema-driven API reference, which
made API docs look incomplete or stale compared to runtime surfaces.

## Non-goals

- Hosting live FastAPI Swagger/ReDoc directly on GitHub Pages.
- Replacing local interactive `/docs` and `/redoc` endpoints.
- Replacing the existing Python module reference published under `/pydoc/`.

## Decision

Generate and commit a deterministic OpenAPI snapshot from `create_app().openapi()`
and use that snapshot as the source for hosted API docs.

Implementation shape:

- Add `tools/export_openapi_snapshot.py` to export/check schema snapshots.
- Store snapshot at `docs/assets/openapi/story_gen.openapi.json`.
- Render snapshot in `docs/api.md` using ReDoc for hosted static browsing.
- Enforce drift checks in CI and pre-push workflows.
- Regenerate snapshot before Pages docs build.

## Public API

- New hosted static OpenAPI artifact:
  - `/docs/assets/openapi/story_gen.openapi.json`
- `docs/api.md` becomes schema-driven using the exported OpenAPI snapshot.
- New developer commands:
  - `make openapi-export`
  - `make openapi-check`

## Invariants

- Runtime Swagger (`/docs`) and runtime OpenAPI (`/openapi.json`) remain authoritative
  while API is running locally.
- Hosted Pages docs remain static-only and do not execute backend routes.
- OpenAPI snapshot must match generated schema from current code.

## Test Plan

- Add unit test to assert committed snapshot equals `create_app().openapi()`.
- Add contract tests for:
  - Make targets (`openapi-export`, `openapi-check`)
  - CI step (`tools/export_openapi_snapshot.py --check`)
  - Pages deploy step (`tools/export_openapi_snapshot.py`)
- Run full repository quality gates before merge.

## Consequences

- API docs quality and discoverability improve on hosted docs without backend hosting.
- Schema drift is now explicit and blocked by CI/pre-push checks.
- Developers must regenerate the snapshot when API contracts change.
