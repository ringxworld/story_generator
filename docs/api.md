# API

The HTTP API now provides a local-preview story editing surface backed by SQLite.

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
- `GET /api/v1/stories?owner_id=<id>&limit=<n>`
  - Lists recent stories.
- `POST /api/v1/stories`
  - Creates one story.
- `GET /api/v1/stories/{story_id}`
  - Reads one story.
- `PUT /api/v1/stories/{story_id}`
  - Updates title/body for one story.

## Notes

- OpenAPI docs are available at `/docs` when running locally.
- Default local DB path is `work/local/story_gen.db`.
- This API is intended for local/dev and future backend hosting.
- GitHub Pages is static hosting only, so it can serve docs/front-end but not this Python API.
