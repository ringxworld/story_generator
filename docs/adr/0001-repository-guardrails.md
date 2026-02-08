# ADR 0001: Repository Guardrails and Boundary Contracts

## Status

Accepted

## Problem

High-velocity code generation can rapidly accumulate architectural debt unless
module boundaries and repository contracts are explicit and enforced.

## Non-goals

- Full immediate migration of all existing modules into new ownership buckets.
- Rewriting stable behavior purely for naming or style reasons.

## Decision

Adopt strict repository guardrails:

- required governance files at repository root
- explicit architecture document and ADR workflow
- explicit module ownership (`api`, `core`, `adapters`, `native`, `cli`)
- CI/contract checks to prevent drift

## Public API

No direct runtime behavior changes. This decision introduces governance
artifacts and contract checks only.

## Invariants

- Architecture changes require architecture doc update and ADR.
- New public behavior/dependency changes require ADR entry.
- Boundaries documented in `docs/architecture.md` are authoritative.

## Test plan

- Contract tests verify required files/directories exist.
- Contract tests assert architecture docs and ADR scaffolding remain present.
- Existing CI quality gates continue to run.

## Consequences

- Slightly more process overhead per non-trivial change.
- Higher confidence that fast iteration will not silently degrade architecture.
