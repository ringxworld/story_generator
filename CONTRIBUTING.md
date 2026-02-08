# Contributing

This repository optimizes for long-term architecture integrity, not speed alone.

## Prime Directive

- You may generate code quickly.
- You may not change architecture boundaries without explicit approval.
- If a requested change violates repository contracts, stop and ask for clarification.

## Required Repository Contracts

The repository must keep these files and directories:

- `LICENSE`
- `CONTRIBUTING.md`
- `SECURITY.md`
- `CODEOWNERS`
- `docs/architecture.md`
- `docs/adr/`

If a change introduces a new public behavior or dependency, add an ADR entry under `docs/adr/`.

## Module Ownership and Boundaries

Python layout invariants:

- Public API: `src/story_gen/api/`
- Internal logic: `src/story_gen/core/`
- Side effects/IO: `src/story_gen/adapters/`
- Native bindings: `src/story_gen/native/`

Boundary rules:

- `api/` may import from `core/`, `adapters/`, and `native/`
- `core/` must not import from `api/`, `adapters/`, or `native/`
- `adapters/` must not be imported by `core/`
- Only `native/` may import compiled extension modules

If you add a module, explain why it belongs in that directory.

## Python and C++ Boundary Rules

- C++ source lives in `cpp/`
- Public C++ headers live in `cpp/include/`
- Binding code lives in `bindings/` or `src/story_gen/native/`
- C++ must not include Python headers outside binding code
- Python must not manipulate raw pointers or C++ ownership semantics

Ownership defaults:

- default to copy semantics
- zero-copy requires explicit documentation
- ownership transfer must be explicit

## Code Quality Requirements

Python:

- Public functions require type hints, docstrings, and explicit error handling
- No implicit exports; re-export explicitly
- Tests must cover both success and failure paths for meaningful behavior
- Do not delete or weaken tests to make CI pass

C++:

- Follow `clang-format` and `clang-tidy`
- No raw owning pointers
- Keep exception policy consistent in the core

## CI Expectations

Expect CI to reject changes when:

- format/lint/type/test checks fail
- coverage gates fail
- sanitizer jobs fail
- architecture boundaries are violated

## Entropy Prevention

- No `utils` modules
- No TODO without an issue reference (for example `TODO(#123): ...`)
- No new public API without docs and tests
- No silent behavior changes
- Feature flags must include removal plans

## Non-Trivial Features Require ADR

Before implementing non-trivial work, create an ADR with:

- Problem
- Non-goals
- Public API
- Invariants
- Test plan
