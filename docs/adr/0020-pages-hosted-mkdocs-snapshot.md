# ADR 0020: Host MkDocs Snapshot on GitHub Pages

## Status

Accepted

## Problem

Repository docs are authored in `docs/` and mirrored to wiki, but the Pages
deployment only served product demo assets and redirected `/docs` to wiki.
That left no hosted static docs snapshot on Pages for users who expect
versioned technical docs under the project site.

## Non-goals

- Replacing wiki sync for collaborative/project-ops notes.
- Hosting dynamic Python API docs (Swagger/ReDoc) on Pages.
- Introducing a second authored docs source.

## Public API

Pages URLs:

- Product demo root: `https://ringxworld.github.io/story_generator/`
- Studio alias: `https://ringxworld.github.io/story_generator/studio/`
- Hosted static docs: `https://ringxworld.github.io/story_generator/docs/`

Workflow behavior:

- `.github/workflows/deploy-pages.yml` now builds MkDocs and publishes the
  output under `/docs/` in the Pages artifact.

## Invariants

- `docs/` remains the single authored source for technical documentation.
- Wiki sync remains enabled for collaborative/project-ops notes.
- Pages continues to publish the offline studio/demo at root and `/studio`.
- Pages docs are a static snapshot from the same commit as the deployed demo.

## Test plan

- Validate `deploy-pages.yml` builds MkDocs and copies output into `site/docs/`.
- Validate CI contract tests assert hosted docs staging behavior.
- Validate Pages deployment contains a browsable docs snapshot at `/docs/`.
- Run full repository checks before merge.
