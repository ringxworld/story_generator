# 0031 Keycloak OIDC Authentication

## Problem

The API currently ships with local bearer-token auth, but production use needs
integration with an external identity provider. We need a supported path for
Keycloak-backed OpenID Connect (OIDC) without changing the core API contract.

## Non-goals

- Replacing FastAPI auth primitives or rewriting the auth model.
- Implementing OAuth authorization code flows inside the API itself.
- Handling token refresh or session management on the backend.

## Public API

- `STORY_GEN_AUTH_MODE=keycloak` switches the API to OIDC validation mode.
- `STORY_GEN_OIDC_ISSUER` sets the issuer URL (required).
- `STORY_GEN_OIDC_AUDIENCE` sets the expected audience (optional).
- `STORY_GEN_OIDC_JWKS_URL` overrides JWKS discovery (optional).
- `STORY_GEN_OIDC_JWKS_JSON` allows inline JWKS for offline/dev use (optional).

`/api/v1/auth/register` and `/api/v1/auth/login` return HTTP 501 in Keycloak mode.

## Invariants

- When `STORY_GEN_AUTH_MODE=keycloak`, requests without a valid bearer token are
  rejected with HTTP 401.
- Tokens are validated against issuer, JWKS, and optional audience.
- No raw tokens are persisted in the database.
- Local auth remains the default when `STORY_GEN_AUTH_MODE` is not set.

## Test plan

- `uv run pytest tests/test_api_app.py -k keycloak`
- `uv run pytest tests/test_api_app.py -k register`
