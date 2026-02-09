# ADR 0018: Wiki Docs + Product-First Pages

## Status

Accepted

## Problem

The repository has two public documentation surfaces:

- GitHub wiki (incomplete)
- GitHub Pages (currently used for docs and offline demo)

This split confuses users about where current docs live. It also means the
first page most visitors see is documentation, not a product snapshot.

## Non-goals

- Replacing in-repo `docs/` as authored source material.
- Hosting the live API/backend on GitHub Pages.
- Building a custom CMS for documentation publishing.

## Decision

Adopt a two-surface model with clear ownership:

- Author docs in repository `docs/`.
- Mirror docs to the GitHub wiki via a repeatable sync tool.
- Automate wiki synchronization from `docs/` using a GitHub Actions workflow.
- Publish the offline studio demo at GitHub Pages root.
- Keep `/studio` as a compatibility alias to the same static demo build.
- Add `/docs` redirect on Pages pointing to the wiki.

## Public API

Developer commands:

- `make wiki-sync`
- `make wiki-sync-push`

Tooling:

- `tools/sync_wiki.py`
- `.github/workflows/wiki-sync.yml`

Public URLs:

- Pages demo root: `https://ringxworld.github.io/story_generator/`
- Wiki docs: `https://github.com/ringxworld/story_generator/wiki`

## Invariants

- `docs/` remains the authored documentation source.
- Wiki content is generated from `docs/` and not hand-maintained as primary.
- Wiki automation runs on `develop`/`main` pushes for docs/sync-tool changes and by manual dispatch.
- GitHub Pages deploys static product demo artifacts only.
- Pages keeps an explicit route to wiki docs.

## Test plan

- Run `make wiki-sync` and verify local wiki clone is updated.
- Run `make wiki-sync-push` and verify wiki pages/sidebar are published.
- Validate Pages workflow builds demo artifact at root and `/studio`.
- Validate redirect page exists under `/docs`.
- Run repository quality checks and targeted tests for workflow/config updates.
