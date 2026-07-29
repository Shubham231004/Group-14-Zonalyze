"""Security response headers are applied to API responses."""
from __future__ import annotations


def test_security_headers_present_on_api(client):
    r = client.get("/health")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert r.headers.get("Referrer-Policy") == "no-referrer"
    assert "max-age=" in (r.headers.get("Strict-Transport-Security") or "")
    assert "default-src 'none'" in (r.headers.get("Content-Security-Policy") or "")


def test_csp_exempt_for_docs_openapi(client):
    # Swagger/OpenAPI must keep working, so the strict CSP is not applied there.
    r = client.get("/openapi.json")
    assert r.status_code == 200
    assert r.headers.get("Content-Security-Policy") is None
    # Other headers still apply everywhere.
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
