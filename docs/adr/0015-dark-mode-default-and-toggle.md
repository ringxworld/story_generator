# ADR 0015: Dark Mode Default and Theme Toggle

## Status

Accepted

## Problem

The studio frontend and hosted documentation currently use a light-first style.
We need a consistent dark-mode experience across both surfaces, with user
control to toggle themes.

## Non-goals

- Per-user server-side theme storage.
- Introducing new UI frameworks for theming.
- Changing product information architecture.

## Decision

Implement dark-mode defaults with local toggle controls:

- React studio (`web/`):
  - default to dark theme
  - add in-app theme toggle button
  - persist theme in browser local storage
- MkDocs documentation:
  - default to `slate` palette (dark)
  - enable built-in Material palette toggle for light/dark switching
  - keep brand overrides for both palettes

## Public API

No backend/API contract changes.

New user-visible behavior:

- Studio renders dark mode by default and exposes `Light mode` / `Dark mode` toggle.
- Docs render dark mode by default and expose Material palette switcher.

## Invariants

- Theme choice remains client-side and deterministic on reload.
- Dark and light palettes preserve readability and focus states.
- Existing routes/content remain unchanged.

## Test plan

- Frontend tests for theme default/toggle behavior.
- Existing frontend typecheck/build/tests must pass.
- `uv run mkdocs build --strict` validates docs theme config.
