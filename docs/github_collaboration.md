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

## Docs publishing

Docs are authored in `docs/` and published to two read surfaces:

- static snapshot on Pages: `https://ringxworld.github.io/story_generator/docs/`
- mirrored wiki for collaboration notes: `https://github.com/ringxworld/story_generator/wiki`

Automation:

- `.github/workflows/wiki-sync.yml` syncs wiki content on pushes to `develop`/`main`
  when docs or sync tooling changes.
- You can also run the same sync workflow manually from the Actions tab.
- `.github/workflows/deploy-pages.yml` builds MkDocs and publishes it under `/docs/` after successful CI on `develop`/`main`.

```bash
make wiki-sync       # update local wiki clone from docs/
make wiki-sync-push  # publish synced docs to GitHub wiki
```

## Pull request defaults in this repo

- PR template: `.github/pull_request_template.md`
- Issue templates: `.github/ISSUE_TEMPLATE/`
- Auto labels by changed area:
  - config: `.github/labeler.yml`
  - workflow: `.github/workflows/pr-labeler.yml`

## Project board directives

- Keep the roadmap board polished and readable.
- Use human names for board/title/view/fields (replace placeholders like `View 1`).
- Keep issue titles concise for quick scan value.
- Keep board metadata current on active items:
  - `Status`
  - `Track`
  - `Priority Band`
- Move cards as soon as implementation state changes, not at end-of-day.

Audit command:

```bash
make project-audit
```

Board sync command:

```bash
make project-sync
```

Label taxonomy audit:

```bash
make label-audit
```

Automated manual-intervention tracker:

- `.github/workflows/meta-audit-notify.yml` runs on schedule and manual dispatch.
- It audits project board hygiene and label taxonomy drift.
- If warnings/errors are found, one tracker issue is created/updated (no duplicates).

Automated board sync:

- `.github/workflows/project-board-sync.yml` runs hourly and on issue/PR events.
- It adds missing open roadmap issues, linked issue references from open PRs, and open PR cards into Project `#2`.
- It is additive and idempotent (it does not remove cards).

Manual rename fallback:

- GitHub API cannot currently rename a Project view.
- If the default view is still `View 1`, use:
  `Project -> View options (...) -> Rename -> Roadmap Board`

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
  - `Linked Issues`
  - full mode:
  `Motivation / Context`, `What Changed`, `Tradeoffs and Risks`, `How This Was Tested`
  - compact mode:
  `Change Notes`, `Validation`
