"""Shared pytest fixtures.

These tests are intentionally dependency-light: they exercise only routes and
units that do not require PostgreSQL, MongoDB, trained ML models, or Ollama, so
they run anywhere (including CI) without external services.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client():
    # Use the context-manager form so FastAPI's lifespan (startup) runs and the
    # people_location sensor is registered, matching real server behavior.
    with TestClient(app) as test_client:
        yield test_client
