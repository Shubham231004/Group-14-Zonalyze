"""Rate limiting is off by default but enforces limits when enabled."""
from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient

pytest.importorskip("slowapi")


def test_rate_limit_returns_429_when_enabled(monkeypatch):
    # Enable limiting with a deliberately tiny limit, then rebuild the app so
    # the new config takes effect.
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMIT", "3/minute")
    monkeypatch.setenv("DB_PASSWORD", "test-pw")  # satisfy config fail-fast

    import app.core.config as config
    import app.main as main_module

    importlib.reload(config)
    importlib.reload(main_module)
    try:
        with TestClient(main_module.app) as c:
            statuses = [c.get("/health").status_code for _ in range(6)]
        assert 200 in statuses  # first few succeed
        assert 429 in statuses  # later ones are rate limited
    finally:
        # Restore default (disabled) app state for any subsequent imports.
        monkeypatch.undo()
        importlib.reload(config)
        importlib.reload(main_module)
