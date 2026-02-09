# GitHub Collaboration Flow

This repository now follows a staged branch model:

- `develop`: integration branch for day-to-day feature merges
- `main`: release branch only (promote from `develop` after verification)

## Branch workflow

1. Create a human-readable feature branch from `develop`.
2. Push commits frequently.
3. Open a PR into `develop`.
4. Merge into `develop` after CI passes.
5. Promote `develop` into `main` only for release candidates.

## Automated PR flow

From a feature branch, use:

```bash
make pr-open    # create PR against develop with template
make pr-checks  # watch required checks
make pr-merge   # merge only after checks pass
```

One-command flow:

```bash
make pr-auto
```

## Wiki docs sync

Docs are authored in `docs/` and mirrored into the repo wiki.

```bash
make wiki-sync       # update local wiki clone from docs/
make wiki-sync-push  # publish synced docs to GitHub wiki
```

Wiki URL:

- `https://github.com/ringxworld/story_generator/wiki`

## Pull request defaults in this repo

- PR template: `.github/pull_request_template.md`
- Issue templates: `.github/ISSUE_TEMPLATE/`
- Auto labels by changed area:
  - config: `.github/labeler.yml`
  - workflow: `.github/workflows/pr-labeler.yml`

## Enforced merge policy

- Pull requests are required for `develop` and `main`.
- Required checks must pass before merge:
  - `quality`
  - `frontend`
  - `native`
  - `docker`
  - `pages`
  - `pr-template`
- Required PR body sections are validated by workflow:
  - `Summary`
  - `Motivation / Context`
  - `What Changed`
  - `Tradeoffs and Risks`
  - `How This Was Tested`
  - `Follow-ups / Future Work`
