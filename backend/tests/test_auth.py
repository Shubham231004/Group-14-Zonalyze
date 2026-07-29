"""Tests for the Clerk auth dependency and route protection.

These do not require a real Clerk instance: they verify the feature-flag
behaviour (off by default) and that protected routes reject requests without a
valid token when auth is enabled. Real token verification is Clerk's job.
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.core import auth


def test_disabled_auth_returns_none():
    """When Clerk is not configured, the dependency is a no-op."""
    original = auth.AUTH_ENABLED
    auth.AUTH_ENABLED = False
    try:
        assert auth.require_user(authorization=None) is None
        assert auth.require_user(authorization="Bearer whatever") is None
    finally:
        auth.AUTH_ENABLED = original


def test_enabled_auth_rejects_missing_and_malformed_header(monkeypatch):
    monkeypatch.setattr(auth, "AUTH_ENABLED", True)
    # Pretend PyJWT is installed so we exercise the header checks, not the
    # library-missing branch.
    monkeypatch.setattr(auth, "jwt", object())
    monkeypatch.setattr(auth, "PyJWKClient", object())

    for bad in (None, "", "Basic abc", "token123"):
        with pytest.raises(HTTPException) as exc_info:
            auth.require_user(authorization=bad)
        assert exc_info.value.status_code == 401


def test_protected_route_open_when_auth_disabled(client):
    # Default test config has auth disabled -> protected route is reachable.
    assert auth.AUTH_ENABLED is False
    assert client.get("/bus/registered-sensors").status_code == 200


def test_protected_route_401_but_health_open_when_auth_enabled(client, monkeypatch):
    monkeypatch.setattr(auth, "AUTH_ENABLED", True)
    monkeypatch.setattr(auth, "jwt", object())
    monkeypatch.setattr(auth, "PyJWKClient", object())

    # Protected route now requires a token.
    assert client.get("/bus/registered-sensors").status_code == 401
    # Public endpoints remain reachable.
    assert client.get("/health").status_code == 200
    assert client.get("/").status_code == 200
