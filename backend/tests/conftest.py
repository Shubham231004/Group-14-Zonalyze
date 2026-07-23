"""Shared pytest fixtures.

These tests are intentionally dependency-light: they exercise only routes and
units that do not require PostgreSQL, MongoDB, trained ML models, or Ollama, so
they run anywhere (including CI) without external services.
"""
from __future__ import annotations

import os

# Tests must run under a CONTROLLED environment: the developer's local .env
# (loaded by app.core.config via dotenv) must not flip feature flags and change
# test outcomes — e.g. a configured CLERK_ISSUER silently enables auth and makes
# open-route tests 401. Values set here win, because load_dotenv never overrides
# existing environment variables.
os.environ.setdefault("DB_PASSWORD", "test-pw")
os.environ["CLERK_ISSUER"] = ""
os.environ["CLERK_JWKS_URL"] = ""
os.environ["RATE_LIMIT_ENABLED"] = "false"

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client():
    # Use the context-manager form so FastAPI's lifespan (startup) runs and the
    # people_location sensor is registered, matching real server behavior.
    with TestClient(app) as test_client:
        yield test_client
