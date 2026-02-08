# ADR 0008: Good Essay Mode as Separate Product Surface

## Status

Accepted

## Problem

Story workflows and essay workflows have different invariants. Treating essays as
ad-hoc story fields makes quality rules ambiguous and weak, especially when long
generation contexts drift.

## Non-goals

- Full essay generation implementation.
- Semantic grading with external models.
- Replacing story blueprint workflows.

## Decision

Introduce a dedicated essay product lane with strict contracts:

- new `EssayBlueprint` and related request/response models
- separate SQLite adapter table (`essays`)
- owner-scoped API routes under `/api/v1/essays/*`
- deterministic quality evaluator in `core/essay_quality.py`
- web studio section for essay workspace CRUD and evaluation
- Python client methods for essay CRUD and evaluation

## Public API

Added endpoints:

- `GET /api/v1/essays`
- `POST /api/v1/essays`
- `GET /api/v1/essays/{essay_id}`
- `PUT /api/v1/essays/{essay_id}`
- `POST /api/v1/essays/{essay_id}/evaluate`

Added typed contracts:

- `EssayBlueprint`, `EssayPolicy`, `EssaySectionRequirement`
- `EssayCreateRequest`, `EssayUpdateRequest`, `EssayResponse`
- `EssayEvaluateRequest`, `EssayEvaluationResponse`

Added Python client methods:

- `StoryApiClient.create_essay`
- `StoryApiClient.update_essay`
- `StoryApiClient.evaluate_essay`

## Invariants

- essay resources are owner-scoped and isolated across users
- essay mode is persisted separately from story mode
- evaluation is deterministic and returns explicit check codes
- policy constraints enforce a bounded drafting contract

## Test Plan

- API contract tests for essay policy invariants
- API integration tests for essay CRUD/evaluation and owner isolation
- adapter tests for essay SQLite persistence
- core tests for pass/fail evaluator behavior
- frontend tests for essay mode interactions
- Python interface tests for essay methods

## Consequences

- clearer product boundaries and less architecture drift
- increased payload complexity for web forms (JSON editing in initial phase)
- deterministic checks are intentionally simple and may require extension later
