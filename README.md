# story_gen

[![CI](https://github.com/ringxworld/story_generator/actions/workflows/ci.yml/badge.svg)](https://github.com/ringxworld/story_generator/actions/workflows/ci.yml)
[![Deploy Pages](https://github.com/ringxworld/story_generator/actions/workflows/deploy-pages.yml/badge.svg)](https://github.com/ringxworld/story_generator/actions/workflows/deploy-pages.yml)

A story engineering project for building original fiction with discipline.

We are treating storytelling like a software system: define canon, model dependencies, validate continuity, and evolve chapters without drift.

Live project pages:
- https://ringxworld.github.io/story_generator/ (offline interactive product demo)
- https://ringxworld.github.io/story_generator/studio/ (compatibility alias)

Wiki docs:
- https://github.com/ringxworld/story_generator/wiki

## Quick Start (Local Stack)

From the repository root, run:

```bash
make stack-up
```

This one command will:

- sync Python dependencies (`uv sync --all-groups`)
- install frontend dependencies (`npm install --prefix web`)
- build the web bundle (`npm run --prefix web build`)
- launch API + web dev servers together

Default local endpoints:

- API: `http://127.0.0.1:8000`
- Web studio: `http://127.0.0.1:5173`
- API docs: `http://127.0.0.1:8000/docs`

Default observability outputs:

- Rotating runtime logs: `work/logs/story_gen.log`
- Anomaly breadcrumbs: `anomaly_events` table in `work/local/story_gen.db`

For faster repeat runs (skip bootstrap/build), use:

```bash
make dev-stack
```

For dedicated frontend hot-edit iteration on a separate port:

```bash
make web-hot
```

Hot-edit endpoint:

- Web hot mode: `http://127.0.0.1:5174`

To run API + hot-edit web together:

```bash
make dev-stack-hot
```

## Quick Start (Docker)

If you want a containerized local stack:

```bash
make docker-up
```

This builds and launches:

- FastAPI API container on `http://127.0.0.1:8000`
- React dev server container on `http://127.0.0.1:5173`

Other Docker commands:

```bash
make docker-down   # stop services
make docker-logs   # tail logs
make docker-ci     # run full CI-quality checks in Docker
```

Cleanup commands:

```bash
make clean       # clear caches and generated build outputs
make clean-deep  # clean + local .venv and web/node_modules
```

## Focus Areas

- Architecture contracts: `docs/architecture.md`
- Visual architecture diagrams: `docs/architecture_diagrams.md`
- ADR records: `docs/adr/`
- Story model and planning architecture: `docs/dependency_charts.md`
- Reference ingestion + analysis workflow: `docs/reference_pipeline.md`
- Native acceleration path (C++/CMake): `docs/native_cpp.md`
- Deployment split (Pages + API): `docs/deployment.md`
- Planned DigitalOcean deployment baseline: `docs/droplet_stack.md`
- Developer local setup runbook: `docs/developer_setup.md`
- React + TypeScript story studio: `docs/studio.md`
- Story-first feature extraction pipeline: `docs/feature_pipeline.md`
- Shareable binary analysis bundle format (`.sgb`): `docs/story_bundle.md`
- Interactive graph and storage path: `docs/graph_strategy.md`
- Full-series text collection: `src/story_gen/cli/story_collector.py`
- Video-story transcript ingestion: `src/story_gen/cli/youtube_downloader.py`
- HTTP API local-preview boundary: `src/story_gen/api/app.py`
- Python blueprint interface: `src/story_gen/api/python_interface.py`

## Governance

- Contribution process: `CONTRIBUTING.md`
- Security reporting: `SECURITY.md`
- Collaboration flow (`develop` + release `main`): `docs/github_collaboration.md`
- PR automation helpers: `make pr-open`, `make pr-checks`, `make pr-merge`, `make pr-auto`
- Wiki sync helpers: `make wiki-sync`, `make wiki-sync-push`
