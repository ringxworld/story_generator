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

## Pull request defaults in this repo

- PR template: `.github/pull_request_template.md`
- Issue templates: `.github/ISSUE_TEMPLATE/`
- Auto labels by changed area:
  - config: `.github/labeler.yml`
  - workflow: `.github/workflows/pr-labeler.yml`

## GitHub settings that must be configured in the web UI

These cannot be reliably enforced from repository files alone:

- set default branch to `develop`
- protect `develop` and `main`
- require PR reviews and passing checks before merge
- enable/disallow wiki based on team preference
- create and configure GitHub Projects boards

Use the templates/workflows in this repo as the in-repo baseline, then finish
org/repo-level controls in GitHub settings.
