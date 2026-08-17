"""Tests for the Clerk auth dependency and route protection."""
from __future__ import annotations

from cryptography.hazmat.primitives.asymmetric import rsa
import jwt
import pytest
from fastapi import HTTPException

from app.core import auth


def test_disabled_auth_returns_none():
    original = auth.AUTH_ENABLED
    auth.AUTH_ENABLED = False
    try:
        assert auth.require_user(authorization=None) is None
        assert auth.require_user(authorization="Bearer whatever") is None
    finally:
        auth.AUTH_ENABLED = original


def test_enabled_auth_rejects_missing_and_malformed_header(monkeypatch):
    monkeypatch.setattr(auth, "AUTH_ENABLED", True)
    monkeypatch.setattr(auth, "jwt", object())
    monkeypatch.setattr(auth, "PyJWKClient", object())

    for bad in (None, "", "Basic abc", "token123"):
        with pytest.raises(HTTPException) as exc_info:
            auth.require_user(authorization=bad)
        assert exc_info.value.status_code == 401


def test_protected_route_open_when_auth_disabled(client):
    assert auth.AUTH_ENABLED is False
    assert client.get("/bus/registered-sensors").status_code == 200


def test_protected_route_401_but_health_open_when_auth_enabled(client, monkeypatch):
    monkeypatch.setattr(auth, "AUTH_ENABLED", True)
    monkeypatch.setattr(auth, "jwt", object())
    monkeypatch.setattr(auth, "PyJWKClient", object())

    assert client.get("/bus/registered-sensors").status_code == 401
    assert client.get("/health").status_code == 200
    assert client.get("/").status_code == 200


def test_require_user_accepts_configured_clerk_public_key(monkeypatch):
    issuer = "https://example.clerk.accounts.dev"
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = jwt.encode({"sub": "user_123", "iss": issuer}, private_key, algorithm="RS256")

    monkeypatch.setattr(auth, "AUTH_ENABLED", True)
    monkeypatch.setattr(auth, "CLERK_ISSUER", issuer)
    monkeypatch.setattr(auth, "CLERK_JWT_KEY", private_key.public_key())

    assert auth.require_user(f"Bearer {token}")["sub"] == "user_123"
