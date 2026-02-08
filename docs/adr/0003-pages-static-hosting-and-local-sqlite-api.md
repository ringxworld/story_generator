# ADR 0003: Static Pages + Local SQLite API Baseline

## Status

Accepted

## Problem

We need a practical path for local story editing with persistence and a future
multi-user deployment model. GitHub Pages is already used for project pages, but
it does not host server-side Python runtimes.

## Non-goals

- Immediate production auth implementation.
- Immediate managed database provisioning.
- Replacing Pages for static docs/site hosting.

## Decision

Adopt a split architecture:

- Keep GitHub Pages as static hosting for docs and front-end assets.
- Run FastAPI as a separate service (local first).
- Use SQLite as the default persistence layer for local and single-instance use.

Add a minimal API surface for story CRUD:

- `GET /api/v1/stories`
- `POST /api/v1/stories`
- `GET /api/v1/stories/{story_id}`
- `PUT /api/v1/stories/{story_id}`

Back this surface with a dedicated adapter:

- `src/story_gen/adapters/sqlite_story_store.py`

## Public API

The HTTP API now includes story create/read/update/list endpoints backed by
SQLite. Existing health and API metadata endpoints remain.

## Invariants

- API remains callable in local environments without external infrastructure.
- Persistence side effects stay in `adapters/`.
- Pages remains static; server/database hosting stays outside Pages.

## Test plan

- API tests cover CRUD success paths.
- API tests cover not-found failure paths.
- CLI test verifies `--db-path` wiring.
- Existing CI quality checks continue to gate merges.
