# Deployment Model

## Current split

- GitHub Pages: static docs/site only
- React + TypeScript studio (`web/`): local dev now, static hosting ready
- FastAPI service: local runtime today, external backend host later
- Persistence: SQLite (`work/local/story_gen.db`) for local or single-instance deployments

## Why this split exists

GitHub Pages does not run server-side application runtimes. It serves static
files only. That means Python APIs and databases must run on a separate host.

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
