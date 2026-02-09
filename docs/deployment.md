# Deployment Model

## Current split

- GitHub Wiki: collaboration and project-operations notes
- GitHub Pages: product-first static studio demo snapshot plus hosted docs under `/docs` and hosted Python API reference under `/pydoc`
- React + TypeScript studio (`web/`): local dev now, static hosting ready
- FastAPI service: local runtime today, external backend host later
- Persistence: SQLite (`work/local/story_gen.db`) for local or single-instance deployments

Local Docker composition for this split is available in:

- `docker-compose.yml`
- `docker/api.Dockerfile`
- `docker/web.Dockerfile`
- `docker/ci.Dockerfile` (CI parity checks)

## Why this split exists

GitHub Pages does not run server-side application runtimes. It serves static
files only. That means Python APIs and databases must run on a separate host.
We also want the first public surface to look like the product, not docs.

## Intended hosted target

Primary target is a cost-aware self-hosted path on a single DigitalOcean Droplet
before moving to heavier managed infrastructure.

Baseline hosted stack:

- Droplet VM
  - reverse proxy (Caddy/Nginx)
  - FastAPI app container
  - Postgres container (or managed DB later)
  - MinIO container for S3-compatible object storage
- GitHub Pages
  - static product demo build at root
- GitHub Wiki
  - reader-facing documentation mirror

## Compose variants for future cloud targets

We keep additional compose templates under `ops/` for cloud portability planning:

- `ops/docker-compose.droplet.yml`
- `ops/docker-compose.aws.yml`
- `ops/docker-compose.gcp.yml`
- `ops/docker-compose.azure.yml`

Each variant uses the same app contract and can run in two modes:

- local fallback mode (bundled Postgres + MinIO containers)
- managed-service mode (external DB/object storage via env vars)

Environment templates:

- `ops/.env.example`
- `ops/.env.aws.example`
- `ops/.env.gcp.example`
- `ops/.env.azure.example`

S3-compatible note:

- MinIO gives local/self-host object storage semantics.
- If we want less ops burden later, DigitalOcean Spaces can replace MinIO with
  minimal API change (both S3-compatible).
- Scaffold files for this path live under `ops/`.

## Near-term plan

1. Keep Pages focused on the product demo at repo root.
2. Publish static docs snapshot on Pages under `/docs`.
3. Publish static Python API reference on Pages under `/pydoc`.
4. Keep docs mirrored into the repository wiki for collaborative edits.
5. Keep API local-first for editing and workflow testing.
6. Keep web studio and Python interface on one shared blueprint contract.
7. Add CORS + stronger auth + storage migration when remote multi-user hosting is needed.

## Wiki synchronization

Repository docs remain authored in `docs/` and are mirrored to the wiki:

- Local sync preview: `make wiki-sync`
- Publish to wiki: `make wiki-sync-push`

Wiki URL:

- `https://github.com/ringxworld/story_generator/wiki`

Hosted docs URL:

- `https://ringxworld.github.io/story_generator/docs/`

Hosted Python API reference URL:

- `https://ringxworld.github.io/story_generator/pydoc/`

## Migration path

- Single-user/self-host: SQLite stays acceptable.
- Multi-user hosted backend: move persistence to Postgres and keep the API contract stable.
- Front-end on Pages calls hosted API URL via environment/config.
- Python users can call the hosted API with `StoryApiClient` or work from local JSON blueprints.

## Service mapping (managed-cloud features we still need)

- Object storage: MinIO now, Spaces or S3 later
- Queue/jobs: start with in-process/background workers, add Redis queue as needed
- Metrics/logging: start with stdout + file logs, add Prometheus/Loki/Grafana stack
- Anomaly breadcrumbs: retain bounded SQLite anomaly events with startup pruning
- Secrets/config: `.env` + host secrets now, move to managed secrets store later
- Backups: snapshot database and object store on schedule
