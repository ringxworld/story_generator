# story_gen

<img src="docs/assets/brand/story-gen-mark.svg" alt="story_gen logo" width="180">

[![CI](https://github.com/ringxworld/story_generator/actions/workflows/ci.yml/badge.svg)](https://github.com/ringxworld/story_generator/actions/workflows/ci.yml)
[![Deploy Pages](https://github.com/ringxworld/story_generator/actions/workflows/deploy-pages.yml/badge.svg)](https://github.com/ringxworld/story_generator/actions/workflows/deploy-pages.yml)
[![Wiki Sync](https://github.com/ringxworld/story_generator/actions/workflows/wiki-sync.yml/badge.svg)](https://github.com/ringxworld/story_generator/actions/workflows/wiki-sync.yml)
[![License](https://img.shields.io/github/license/ringxworld/story_generator)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](pyproject.toml)

`story_gen` is a story intelligence pipeline and studio.

It ingests narrative sources, extracts structured story signals, and projects them into timeline/theme/arc views for analysis.

It provides:

- ingestion for text/docs/transcripts
- language detection and translation routing
- extraction of events, beats, themes, entities, and insights
- timeline composition in narrative and chronological views
- dashboard-ready projections and exportable demo surfaces

Relevant checks surfaced above:

- integration test/lint/type pipeline (`CI`)
- Pages build and deploy (`Deploy Pages`)
- docs-to-wiki synchronization (`Wiki Sync`)

Not included on purpose:

- package-download badges (project is not currently published to PyPI/Conda)

## Links

- Product demo (GitHub Pages): https://ringxworld.github.io/story_generator/
- Studio alias: https://ringxworld.github.io/story_generator/studio/
- Hosted technical docs (Pages): https://ringxworld.github.io/story_generator/docs/
- Hosted Python API reference (Pages): https://ringxworld.github.io/story_generator/pydoc/
- Wiki (collaboration/ops notes): https://github.com/ringxworld/story_generator/wiki
- Project board: https://github.com/users/ringxworld/projects/2
- Security policy: `SECURITY.md`

## Documentation ownership

- Repo docs (`docs/`, contracts, architecture, ADRs): versioned technical source of truth.
- Wiki: collaborative/project-operations context (planning, decisions, onboarding, weekly updates).
- Pages: public product/demo surface plus a static docs snapshot under `/docs/`.

Rule of thumb:

- Commit/release-accurate content belongs in repo docs.
- Operational content that can evolve independently belongs in wiki.

Guardrail:

- Avoid duplicated docs across repo and wiki; keep one source and link from the other.
- API/code docs stay source-of-truth in repo docs.

## Run locally

From repository root:

```bash
make stack-up
```

Endpoints:

- API: `http://127.0.0.1:8000`
- Studio: `http://127.0.0.1:5173`
- API docs: `http://127.0.0.1:8000/docs`

Fast iteration:

```bash
make dev-stack
make dev-stack-hot
```

## Minimal startup commands

One terminal + tmux bringup (recommended on Windows via WSL/Git Bash):

```bash
make sync
make bringup-up
```

This opens windows for:

- ROS2 docker stack (`ros2-stack`)
- API server (`story-api`)
- web dashboard (`web` Vite dev server)
- ROS2 container logs

Non-tmux flow:

```bash
make sync
make ros2-stack-up-detached
make api
make web-dev
```

Optional ROS2 auto-launch inside docker:

```bash
ATITD_ROS2_LAUNCH_COMMAND="ros2 launch <package> <launch_file>.launch.py" make ros2-stack-up
```

## Run with Docker

```bash
make docker-up
make docker-down
make docker-logs
```

ROS2-only container targets:

```bash
make ros2-stack-build
make ros2-stack-up
make ros2-stack-logs
make ros2-stack-down
```

## Quality checks

```bash
make check
```

For command details:

```bash
make help
```

## Python API docs (pdoc)

This repository publishes Python API docs to GitHub Pages under `/pydoc/` from the `Deploy Pages` workflow.

Build locally:

```bash
make docs-pydoc
```
