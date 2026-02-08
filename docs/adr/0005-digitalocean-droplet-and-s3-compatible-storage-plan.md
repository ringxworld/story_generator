# ADR 0005: DigitalOcean Droplet and S3-Compatible Storage Plan

## Status

Accepted

## Problem

We need to communicate a realistic deployment path that avoids high early cloud
costs while keeping architecture portable for future growth.

## Non-goals

- Immediate production-grade HA deployment.
- Immediate migration to a fully managed cloud stack.
- Final decision on every future managed service vendor.

## Decision

Use a DigitalOcean-first deployment strategy:

- start with one Droplet running app + supporting services
- use Postgres for multi-user persistent data
- use MinIO for S3-compatible object storage
- keep static docs/site on GitHub Pages

Keep interfaces cloud-portable:

- object storage via S3-compatible APIs
- API contract independent of hosting vendor
- environment-driven URLs and credentials

## Public API

No API shape changes in this ADR. This decision is operational/deployment
guidance only.

## Invariants

- GitHub Pages remains static-only.
- Backend deploys separately from Pages.
- Object storage access stays S3-compatible to preserve portability.

## Test plan

- Keep CI checks for API/frontend/tests/docs.
- Add and maintain deployment scaffolds under `ops/`.
- Validate hosted environment with smoke checks before release.
