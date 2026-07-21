"""Smoke tests for always-available, dependency-free endpoints."""
from __future__ import annotations


def test_root_ok(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"]


def test_health_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "backend"


def test_registered_sensors_includes_people_location(client):
    # The people_location sensor is registered on app startup (lifespan).
    response = client.get("/bus/registered-sensors")
    assert response.status_code == 200
    assert "people_location" in response.json()["sensors"]
