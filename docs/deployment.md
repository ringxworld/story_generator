# Deployment Model

## Current split

- GitHub Pages: static docs/site only
- React + TypeScript studio (`web/`): local dev now, static hosting ready
- FastAPI service: local runtime today, external backend host later
- Persistence: SQLite (`work/local/story_gen.db`) for local or single-instance deployments

## Why this split exists

GitHub Pages does not run server-side application runtimes. It serves static
files only. That means Python APIs and databases must run on a separate host.

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
  - static docs and optional static frontend build

S3-compatible note:

- MinIO gives local/self-host object storage semantics.
- If we want less ops burden later, DigitalOcean Spaces can replace MinIO with
  minimal API change (both S3-compatible).
- Scaffold files for this path live under `ops/`.

## Near-term plan

1. Keep Pages for docs and static project pages.
2. Keep API local-first for editing and workflow testing.
3. Keep web studio and Python interface on one shared blueprint contract.
4. Add CORS + stronger auth + storage migration when remote multi-user hosting is needed.

## Migration path

- Single-user/self-host: SQLite stays acceptable.
- Multi-user hosted backend: move persistence to Postgres and keep the API contract stable.
- Front-end on Pages calls hosted API URL via environment/config.
- Python users can call the hosted API with `StoryApiClient` or work from local JSON blueprints.

## Service mapping (managed-cloud features we still need)

- Object storage: MinIO now, Spaces or S3 later
- Queue/jobs: start with in-process/background workers, add Redis queue as needed
- Metrics/logging: start with stdout + file logs, add Prometheus/Loki/Grafana stack
- Secrets/config: `.env` + host secrets now, move to managed secrets store later
- Backups: snapshot database and object store on schedule
