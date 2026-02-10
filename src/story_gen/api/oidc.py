"""OpenID Connect token validation helpers for Keycloak-backed auth."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, cast

import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey


@dataclass(frozen=True)
class OidcClaims:
    """Verified OIDC claims used by API auth."""

    subject: str
    issuer: str
    email: str | None
    preferred_username: str | None
    name: str | None
    audience: str | None


@dataclass
class _OidcCache:
    value: dict[str, Any] | None = None
    expires_at: float = 0.0


_JWKS_CACHE = _OidcCache()
_WELL_KNOWN_CACHE = _OidcCache()


def _env(name: str, default: str = "") -> str:
    return str((__import__("os")).environ.get(name, default)).strip()


def _int_env(name: str, default: int, *, minimum: int, maximum: int) -> int:
    raw = _env(name)
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(minimum, min(maximum, value))


def _resolve_jwks_url(issuer: str) -> str:
    explicit = _env("STORY_GEN_OIDC_JWKS_URL")
    if explicit:
        return explicit
    well_known = _fetch_well_known(issuer)
    jwks_uri = well_known.get("jwks_uri")
    if isinstance(jwks_uri, str) and jwks_uri:
        return jwks_uri
    raise RuntimeError("OIDC well-known config missing jwks_uri.")


def _fetch_well_known(issuer: str) -> dict[str, Any]:
    ttl_seconds = _int_env("STORY_GEN_OIDC_WELL_KNOWN_TTL_SECONDS", 300, minimum=30, maximum=3600)
    now = time.monotonic()
    if _WELL_KNOWN_CACHE.value is not None and _WELL_KNOWN_CACHE.expires_at > now:
        return _WELL_KNOWN_CACHE.value
    url = issuer.rstrip("/") + "/.well-known/openid-configuration"
    with httpx.Client(timeout=10.0, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError("OIDC well-known response was not an object.")
    _WELL_KNOWN_CACHE.value = payload
    _WELL_KNOWN_CACHE.expires_at = now + ttl_seconds
    return payload


def _fetch_jwks(issuer: str) -> dict[str, Any]:
    inline = _env("STORY_GEN_OIDC_JWKS_JSON")
    if inline:
        payload = json.loads(inline)
        if not isinstance(payload, dict):
            raise RuntimeError("OIDC JWKS JSON must be an object.")
        return payload
    ttl_seconds = _int_env("STORY_GEN_OIDC_JWKS_TTL_SECONDS", 300, minimum=30, maximum=3600)
    now = time.monotonic()
    if _JWKS_CACHE.value is not None and _JWKS_CACHE.expires_at > now:
        return _JWKS_CACHE.value
    jwks_url = _resolve_jwks_url(issuer)
    with httpx.Client(timeout=10.0, follow_redirects=True) as client:
        response = client.get(jwks_url)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError("OIDC JWKS response was not an object.")
    _JWKS_CACHE.value = payload
    _JWKS_CACHE.expires_at = now + ttl_seconds
    return payload


def _select_jwk(jwks: dict[str, Any], kid: str | None) -> dict[str, Any]:
    keys = jwks.get("keys")
    if not isinstance(keys, list):
        raise RuntimeError("OIDC JWKS payload missing keys list.")
    if kid is None:
        if len(keys) == 1 and isinstance(keys[0], dict):
            return keys[0]
        raise RuntimeError("OIDC token header missing kid and JWKS has multiple keys.")
    for key in keys:
        if isinstance(key, dict) and key.get("kid") == kid:
            return key
    raise RuntimeError("OIDC JWKS did not contain signing key for token kid.")


def validate_oidc_token(token: str) -> OidcClaims:
    """Validate a bearer token against OIDC settings."""
    issuer = _env("STORY_GEN_OIDC_ISSUER")
    if not issuer:
        raise RuntimeError("STORY_GEN_OIDC_ISSUER is required for keycloak auth.")
    audience = _env("STORY_GEN_OIDC_AUDIENCE")
    algorithms = _env("STORY_GEN_OIDC_ALGORITHMS", "RS256").split(",")
    algorithms = [algo.strip() for algo in algorithms if algo.strip()]
    if not algorithms:
        algorithms = ["RS256"]

    header = jwt.get_unverified_header(token)
    kid = header.get("kid") if isinstance(header, dict) else None
    jwks = _fetch_jwks(issuer)
    jwk = _select_jwk(jwks, kid)
    public_key = cast(RSAPublicKey, jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk)))
    options: dict[str, bool] = {"verify_aud": bool(audience)}
    payload = jwt.decode(
        token,
        key=public_key,
        algorithms=algorithms,
        audience=audience or None,
        issuer=issuer,
        options=cast(Any, options),
    )
    if not isinstance(payload, dict):
        raise RuntimeError("OIDC token payload was not an object.")
    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject.strip():
        raise RuntimeError("OIDC token missing subject.")
    email = payload.get("email")
    preferred_username = payload.get("preferred_username")
    name = payload.get("name")
    return OidcClaims(
        subject=subject,
        issuer=issuer,
        email=email if isinstance(email, str) and email.strip() else None,
        preferred_username=preferred_username
        if isinstance(preferred_username, str) and preferred_username.strip()
        else None,
        name=name if isinstance(name, str) and name.strip() else None,
        audience=audience or None,
    )
