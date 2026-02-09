# story_gen

[![CI](https://github.com/ringxworld/story_generator/actions/workflows/ci.yml/badge.svg)](https://github.com/ringxworld/story_generator/actions/workflows/ci.yml)
[![Deploy Pages](https://github.com/ringxworld/story_generator/actions/workflows/deploy-pages.yml/badge.svg)](https://github.com/ringxworld/story_generator/actions/workflows/deploy-pages.yml)

A story engineering project for building original fiction with discipline.

We are treating storytelling like a software system: define canon, model dependencies, validate continuity, and evolve chapters without drift.

Live project pages:
- https://ringxworld.github.io/story_generator/
- https://ringxworld.github.io/story_generator/studio/ (offline interactive demo)

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

## Visual System

The project uses one shared visual system across the React studio and GitHub Pages docs.

Core palette:

- `Ink`: `#1F1B17`
- `Paper`: `#F7F2E6`
- `Parchment`: `#EFE3CC`
- `Evergreen`: `#2E473D`
- `Copper`: `#A45B2A`
- `Border`: `#CCB99A`

Typography:

- UI body: `Source Sans 3`
- Section headings: `Alegreya`
- Code: `JetBrains Mono`

Theme behavior:

- Dark mode is the default for both studio and docs.
- Both surfaces expose a runtime light/dark toggle.

Icon system:

- Branded source assets: `web/public/brand/story-gen-mark.svg`
- Browser/app icon pack: `web/public/icons/`
- Docs logo/favicon assets: `docs/assets/brand/`
- Regenerate all icon outputs with: `make brand-icons`

## Current Stage

- Build the core story engine around themes, chapters, characters, and canon.
- Use reference-text analysis to learn craft patterns (structure, dialogue, pacing, character pressure).
- Turn those patterns into reusable constraints for original story generation.

## What This Project Is Optimizing For

- Narrative consistency over long arcs
- Intentional character voice and relationship evolution
- Clear chapter-level objectives and dependency tracking
- Repeatable workflow from draft to validated chapter

## Working Principles

- Canon is explicit and versioned.
- Drift checks are automated and test-backed.
- Reference material is for private study, not redistribution.
- Every change should move us toward a reliable, high-quality story pipeline.

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
