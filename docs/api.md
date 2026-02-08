# API

The HTTP API is currently a **stub** so we can lock boundary contracts early.

## Run locally

```bash
uv run story-api --host 127.0.0.1 --port 8000 --reload
```

## Endpoints

- `GET /healthz`
  - Returns service health payload.
- `GET /api/v1`
  - Returns stub metadata and currently exposed endpoint list.

## Notes

- OpenAPI docs are available at `/docs` when running locally.
- This surface is intentionally small while domain boundaries stabilize.
