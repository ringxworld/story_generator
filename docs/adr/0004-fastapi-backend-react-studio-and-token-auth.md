# ADR 0004: FastAPI Backend, React Studio, and Token Auth

## Status

Accepted

## Problem

We need a usable product surface for story creation with:

- authenticated multi-user editing
- web UI for story building blocks
- Python-first interface for local automation scripts

We also need compatibility with GitHub Pages static hosting.

## Non-goals

- Full production auth stack (SSO, password reset, MFA).
- Immediate database migration to managed Postgres.
- Final generation engine implementation.

## Decision

Keep FastAPI as the backend and add a React + TypeScript frontend in `web/`.

Why FastAPI over a new Node backend right now:

- preserves Python-first workflows and typed contracts in one place
- avoids duplicating domain contracts and test suites across two server stacks
- keeps current repository boundaries intact

Add bearer-token auth and owner-scoped story endpoints backed by SQLite.

Add Python interface helpers so users can:

- edit/validate blueprint JSON locally
- call API via typed client

## Public API

HTTP additions:

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/me`
- authenticated CRUD for `/api/v1/stories`

Python additions:

- `story_gen.api.StoryBlueprint`
- `story_gen.api.load_blueprint_json`
- `story_gen.api.save_blueprint_json`
- `story_gen.api.StoryApiClient`

CLI additions:

- `story-blueprint`

## Invariants

- Story blueprint contract is shared across web, HTTP, and Python interfaces.
- Story access remains owner-scoped.
- GitHub Pages remains static-only; backend is deployed separately when remote hosting is needed.

## Test plan

- API tests for auth success/failure and owner isolation.
- Adapter tests for users/tokens/stories.
- Frontend tests + typecheck + build in CI.
- Existing Python/C++ quality gates remain required.
