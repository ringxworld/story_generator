# story_gen

<p align="center">
  <img src="web/public/brand/story-gen-mark.svg" alt="story_gen logo" width="120" />
</p>

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
- Wiki (primary docs): https://github.com/ringxworld/story_generator/wiki
- Project board: https://github.com/users/ringxworld/projects/2
- Security policy: `SECURITY.md`

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

## Run with Docker

```bash
make docker-up
make docker-down
make docker-logs
```

## Quality checks

```bash
make check
```

For command details:

```bash
make help
```
