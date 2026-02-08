# ADR 0010: Docker Local Stack and CI Validation

## Status

Accepted

## Problem

Local setup currently assumes direct host tooling for Python, Node, and native
checks. We also need consistent containerized execution in CI so environment
drift does not hide failures that only appear in containerized deployments.

## Non-goals

- Replacing current local `uv`/`npm` host workflows.
- Replacing cloud compose scaffolds under `ops/`.
- Introducing orchestration beyond Docker Compose for local development.

## Decision

Add first-class Docker artifacts for local and CI workflows:

- `docker/api.Dockerfile` for FastAPI runtime
- `docker/web.Dockerfile` for React dev server runtime
- `docker/ci.Dockerfile` for full quality/test/docs checks
- `docker-compose.yml` for local API + web orchestration

Expose explicit Makefile targets for Docker lifecycle and CI parity:

- `docker-build`, `docker-up`, `docker-down`, `docker-logs`, `docker-ci`

Update GitHub Actions CI to include a Docker validation job that:

- builds API and web runtime images
- smoke-tests the composed stack
- runs full project checks in the CI Docker image

## Public API

Developer-facing commands:

- `make docker-build`
- `make docker-up`
- `make docker-down`
- `make docker-logs`
- `make docker-ci`

Repository runtime artifacts:

- `docker-compose.yml`
- `docker/*.Dockerfile`

CI behavior:

- `.github/workflows/ci.yml` includes Docker-based validation steps.

## Invariants

- Existing host-native workflows (`make check`, `make stack-up`) remain valid.
- Docker local stack serves API on `:8000` and web on `:5173`.
- Docker CI path executes the same effective quality/test gates as host CI.
- Docs and tests must cover Docker entrypoints and workflow presence.

## Test plan

- Extend repository contract tests to assert Docker files/targets/workflow steps.
- Run `uv run pre-commit run --all-files`.
- Run `uv run pytest`.
- CI executes Docker build/smoke/check workflow on push and pull request.
