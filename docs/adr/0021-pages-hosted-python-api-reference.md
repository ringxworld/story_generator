# 0021 Pages Hosted Python API Reference

## Problem

The project published a static product demo and MkDocs documentation on GitHub Pages, but not a hosted Python API reference. Users had to run the API locally or inspect source directly to browse Python module interfaces.

## Non-goals

- Replacing FastAPI Swagger/ReDoc for runtime endpoint interaction.
- Publishing execution-capable backend services on GitHub Pages.
- Guaranteeing stable deep links for private/internal symbols.

## Public API

- GitHub Pages now includes a static Python API reference surface at `/pydoc/`.
- README and docs expose explicit links for:
  - product demo (`/`)
  - technical docs (`/docs/`)
  - Python module reference (`/pydoc/`)

## Invariants

- Pages deploy remains gated by successful CI on `develop` or `main`.
- Hosted Python API reference is generated from repository source in CI, not hand-authored.
- Static hosting boundaries remain unchanged: no server runtime on Pages.

## Test plan

- Contract tests validate deploy workflow contains:
  - `pdoc` build step
  - copy into `site/pydoc`
- Validate Pages URL returns successful response after deploy:
  - `https://ringxworld.github.io/story_generator/pydoc/`
- Keep existing docs and demo deployment checks green.
