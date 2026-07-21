"""Clerk-based authentication dependency.

Design goals:
- **Off by default.** If Clerk is not configured (AUTH_ENABLED is False), every
  endpoint behaves exactly as it did before auth existed. This lets the feature
  ship without changing the running app until the operator opts in.
- **No secret key on the server.** Verification uses Clerk's public JWKS keys.
- **Graceful import.** PyJWT is imported defensively so the app still starts
  even if the dependency is not installed yet (auth simply cannot be enabled).
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import Header, HTTPException, status

from app.core.config import AUTH_ENABLED, CLERK_ISSUER, CLERK_JWKS_URL

logger = logging.getLogger(__name__)

try:  # pragma: no cover - import guard
    import jwt
    from jwt import PyJWKClient
except Exception:  # PyJWT not installed
    jwt = None  # type: ignore[assignment]
    PyJWKClient = None  # type: ignore[assignment]


_jwk_client: Optional["PyJWKClient"] = None


def _get_jwk_client() -> "PyJWKClient":
    global _jwk_client
    if _jwk_client is None:
        _jwk_client = PyJWKClient(CLERK_JWKS_URL)
    return _jwk_client


def require_user(authorization: Optional[str] = Header(default=None)) -> Optional[dict[str, Any]]:
    """FastAPI dependency that enforces a valid Clerk session token.

    Returns the decoded claims (so routes can read the user id) when auth is on,
    or None when auth is disabled. Raises 401 on any missing/invalid token.
    """
    if not AUTH_ENABLED:
        return None

    if jwt is None or PyJWKClient is None:
        # Misconfiguration: auth turned on but the library is absent.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication is enabled but PyJWT is not installed. Run: pip install -r requirements.txt",
        )

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split(" ", 1)[1].strip()
    try:
        signing_key = _get_jwk_client().get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=CLERK_ISSUER,
            options={"verify_aud": False},
        )
    except Exception as exc:
        # Never echo the raw error to the client; log the type server-side.
        logger.warning("Clerk JWT verification failed: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return claims
