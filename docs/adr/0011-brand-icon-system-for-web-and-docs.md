# ADR 0011: Brand Icon System for Web and Docs

## Status

Accepted

## Problem

The project had no consistent icon system across the React studio and hosted docs.
Browser tabs, app installs, and docs headers lacked branded assets and a
reproducible generation path.

## Non-goals

- Rebranding typography or core color palette.
- Replacing existing product UI layout.
- Introducing external design/build dependencies for icon generation.

## Decision

Adopt a single brand mark and icon pack shared across product surfaces:

- web app browser metadata (`favicon`, `apple-touch-icon`, `manifest`)
- web app install icons (`192`, `512`, `maskable`)
- docs logo + favicon assets

Add deterministic asset generation via:

- `tools/generate_brand_icons.py`
- `make brand-icons`

The generator produces SVG + PNG + ICO outputs using repository-native tools
only (no new runtime dependencies).

## Public API

Developer commands and files:

- `make brand-icons`
- `tools/generate_brand_icons.py`
- `web/public/favicon.svg`
- `web/public/favicon.ico`
- `web/public/site.webmanifest`
- `web/public/icons/*`
- `docs/assets/brand/*`

## Invariants

- Web and docs use the same brand mark style and palette.
- Icon outputs are reproducible from one script.
- Browser metadata points to committed icon assets.
- MkDocs theme logo/favicon reference committed docs brand assets.

## Test plan

- Extend repository contract checks for icon generation target + key files.
- Run `uv run pre-commit run --all-files`.
- Run `uv run pytest`.
- Run `uv run mkdocs build --strict`.
- Run frontend build/typecheck/tests to verify static asset references.
