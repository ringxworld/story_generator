# Architecture

This file defines the stable shape of the repository and import boundaries.

## Core Modules and Responsibilities

- `src/story_gen/api/`
  - Public Python API layer and HTTP surfaces.
- `src/story_gen/core/`
  - Internal pure business logic and domain orchestration.
- `src/story_gen/adapters/`
  - Side effects: filesystem, network, subprocesses, model loading.
  - Local persistence adapters (for example SQLite story storage).
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

## Stable Public API

Stable public Python surfaces are:

- `story_gen.api.*`
- declared console scripts in `pyproject.toml`

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
