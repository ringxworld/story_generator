# Architecture

This file defines the stable shape of the repository and import boundaries.

## Core Modules and Responsibilities

- `src/story_gen/api/`
  - Public Python API layer and HTTP surfaces.
- `src/story_gen/core/`
  - Internal pure business logic, domain orchestration, and deterministic evaluation/extraction.
  - Story intelligence pipeline stages (`story_schema`, ingestion, translation, extraction,
    beats/themes/timeline/insights, quality gate, dashboard projections).
- `src/story_gen/adapters/`
  - Side effects: filesystem, network, subprocesses, model loading.
  - Local persistence adapters (for example SQLite story/feature/essay storage).
  - Local analysis persistence adapter for story intelligence runs and dashboard payloads.
- `src/story_gen/native/`
  - Python-facing boundary for compiled/native integrations.
- `src/story_gen/cli/`
  - Argparse-driven one-off command entrypoints.
- `cpp/`
  - Native C++ implementation and tests.
- `cpp/include/`
  - Public C++ headers for native consumers.
- `docs/adr/`
  - Architecture decision records.
- `work/contracts/`
  - Versioned analysis artifact contracts (A-H) for corpus and drift workflows.
  - Exported story schema/pipeline contract registry snapshot.
- `web/`
  - React + TypeScript studio for story and essay product lanes.

## Allowed Import Graph

Python import graph:

- `api` -> `core`, `adapters`, `native`
- `core` -> `core` only
- `adapters` -> `core` allowed
- `native` -> `core` allowed
- `cli` -> `api`, `core`, `adapters`, `native`

Disallowed:

- `core` importing `api`, `adapters`, or `native`
- compiled extension imports outside `native`
- front-end logic importing server runtime code directly (contract-only via HTTP/JSON)

## Stable Public API

Stable public Python surfaces are:

- `story_gen.api.*`
- declared console scripts in `pyproject.toml`
- typed essay and story contracts in `story_gen.api.contracts`
- story analysis and dashboard HTTP contracts under `story_gen.api.contracts`

New public surfaces require:

- docs update
- tests
- ADR entry if behavior/dependency changes are non-trivial

## Python/C++ Boundary Rules

- C++ code lives in `cpp/`
- public headers live in `cpp/include/`
- Python/C++ binding code only in `bindings/` or `src/story_gen/native/`
- no Python headers in C++ outside binding layer
- Python never handles raw pointer ownership directly

Ownership defaults:

- copy by default
- zero-copy requires explicit documentation
- ownership transfer must be explicit

## Enforcement Notes

The repository uses contract tests and CI checks to detect drift.
If architecture rules need to change, update this file first and add an ADR.

## Contract Registry

Schema and stage-level pipeline contracts are tracked in:

- `src/story_gen/api/contract_registry.py`
- `work/contracts/story_pipeline_contract_registry.v1.json`
- `src/story_gen/core/pipeline_contracts.py`

## Schema Versioning Policy

Canonical story schema rules:

- `story_analysis.v1` is the current canonical schema key.
- Backward-compatible additions may be introduced in `v1` without changing the key.
- Breaking changes require a new schema key (for example `story_analysis.v2`).
- Persistence adapters must fail fast on schema version mismatches until migrations run.
- During migrations, both versions must be explicitly tracked in contracts and docs.
