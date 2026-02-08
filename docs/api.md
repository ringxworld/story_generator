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

## Notes

- OpenAPI docs are available at `/docs` when running locally.
- Default local DB path is `work/local/story_gen.db`.
- Auth is bearer-token based for local/dev workflows.
- This API is intended for local/dev now and backend hosting later.
- GitHub Pages is static hosting only, so it can serve docs/front-end but not this Python API.
- Python users can work with the same contracts via `story_gen.api` and `story-blueprint`.
- Override allowed CORS origins with `STORY_GEN_CORS_ORIGINS` (comma-separated).
