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

Default reviewer behavior:

- `tools/pr_flow.py` requests reviewer `ringxworld` by default.
- Override with `PR_DEFAULT_REVIEWER=<login>` or `--reviewer <login>`.
- If GitHub blocks self-review requests, the same login is added as PR assignee.

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
  - Always required: `Summary`, `Linked Issues`
  - Choose one mode:
  - Full mode: `Motivation / Context`, `What Changed`, `Tradeoffs and Risks`, `How This Was Tested`, `Follow-ups / Future Work`
  - Compact mode: `Change Notes`, `Validation`
