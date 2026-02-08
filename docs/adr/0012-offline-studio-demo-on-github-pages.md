# ADR 0012: Offline Studio Demo on GitHub Pages

## Status

Accepted

## Problem

The hosted GitHub Pages site currently exposes documentation but not an
interactive product experience. Prospective users cannot explore the dashboard
and graph UX without running the backend locally.

## Non-goals

- Hosting authenticated or write-enabled API features on GitHub Pages.
- Replacing the local/hosted FastAPI runtime for real workflows.
- Introducing new external frontend frameworks or routing layers.

## Decision

Add an offline mode to the existing React studio that renders representative
story intelligence data without backend calls.

Publish this mode to GitHub Pages as a static build at:

- `/story_generator/studio/`

Update the Pages deployment workflow to build both:

- MkDocs site (docs)
- Vite offline demo bundle (studio)

Copy the web bundle into `site/studio/` before artifact upload.

## Public API

Public URLs:

- Docs: `https://ringxworld.github.io/story_generator/`
- Offline studio demo: `https://ringxworld.github.io/story_generator/studio/`

Frontend behavior:

- Offline mode can be enabled by:
  - `VITE_OFFLINE_DEMO=true` at build time
  - `?demo=1` query parameter
  - GitHub Pages `/studio/` hosted path detection

## Invariants

- Offline mode must not require network/API availability.
- Existing online studio behavior remains unchanged for local/API usage.
- GitHub Pages deploy workflow must publish docs and demo together.
- No new backend dependencies are introduced.

## Test plan

- Add frontend test to assert offline mode rendering via query flag.
- Extend repository contract tests for Pages workflow offline demo build steps.
- Run:
  - `uv run pre-commit run --all-files`
  - `uv run pytest`
  - `npm run --prefix web typecheck`
  - `npm run --prefix web test:coverage`
  - `npm run --prefix web build`
  - `uv run mkdocs build --strict`
