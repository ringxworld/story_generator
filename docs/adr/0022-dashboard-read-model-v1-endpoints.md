# ADR 0022: Dashboard Read-Model v1 Endpoints

## Status

Accepted

## Problem

Dashboard endpoints existed only as unversioned routes. Frontend clients need a
version-stable read-model surface for overview cards, timeline lanes, and theme
heatmaps so API evolution does not force synchronized deploys.

## Non-goals

- Replacing current dashboard response schemas.
- Removing existing unversioned dashboard routes in this change.
- Versioning every dashboard route in this ADR.

## Decision

- Add versioned v1 aliases for core dashboard read-model endpoints:
  - `GET /api/v1/stories/{story_id}/dashboard/v1/overview`
  - `GET /api/v1/stories/{story_id}/dashboard/v1/timeline`
  - `GET /api/v1/stories/{story_id}/dashboard/v1/themes/heatmap`
- Keep existing unversioned routes active and schema-compatible.
- Track v1 contracts explicitly in the contract registry.
- Document drilldown payload shape for frontend consumers.

## Public API

New routes:

- `/api/v1/stories/{story_id}/dashboard/v1/overview`
- `/api/v1/stories/{story_id}/dashboard/v1/timeline`
- `/api/v1/stories/{story_id}/dashboard/v1/themes/heatmap`

Behavior:

- v1 routes return the same payload shapes as their unversioned counterparts.
- Existing clients using unversioned routes continue to work unchanged.

## Invariants

- Owner-scoped access behavior stays unchanged for both route families.
- v1 route responses remain contract-compatible with existing response models.
- Malformed persisted dashboard payloads fail consistently on both route families.

## Test plan

- API tests validate parity between unversioned and v1 route responses.
- API tests validate owner isolation and malformed-payload handling on v1.
- Contract registry tests verify v1 contract IDs are present.
