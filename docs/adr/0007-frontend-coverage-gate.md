# ADR 0007: Frontend Coverage Gate in CI and Pre-Push

## Status

Accepted

## Problem

Frontend tests existed, but CI and pre-push only enforced pass/fail execution.
This allowed untested React/TypeScript paths to grow without a measurable
coverage floor.

## Non-goals

- Enforcing per-file coverage thresholds.
- Introducing snapshot-heavy UI testing patterns.
- Replacing Python coverage policy.

## Decision

Add deterministic frontend coverage enforcement using Vitest v8 coverage:

- add `@vitest/coverage-v8` to `web` dev dependencies
- add `test:coverage` script in `web/package.json`
- configure coverage thresholds in `web/vitest.config.ts`
- enforce `test:coverage` in CI frontend job
- enforce `test:coverage` in Python pre-push quality runner

## Public API

No external runtime API changes.

Developer workflow changes:

- `npm run --prefix web test:coverage`
- `make web-coverage`
- `make check` now includes frontend and native quality gates

## Invariants

- frontend coverage gate must run in CI on push and pull request
- local pre-push must run the same coverage command as CI
- threshold configuration must live in versioned frontend test config

## Test plan

- contract tests assert CI workflow uses `test:coverage`
- contract tests assert pre-push runner uses `test:coverage`
- contract tests assert vitest thresholds and coverage dependency are present
- frontend unit tests cover success and failure paths for API and UI flows
