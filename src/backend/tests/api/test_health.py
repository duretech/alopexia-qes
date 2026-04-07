"""Smoke tests for health check endpoints.

These tests verify that /health/live and /health/ready respond correctly.
The liveness probe requires no external dependencies.
The readiness probe checks DB connectivity — in these tests, the DB may not
be available, so we verify both the 200 and 503 paths.
"""

import pytest


@pytest.mark.anyio
async def test_liveness_returns_200(client):
    """GET /health/live should always return 200 with status=ok."""
    response = await client.get("/health/live")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "timestamp" in body


@pytest.mark.anyio
async def test_liveness_includes_correlation_headers(client):
    """Liveness response should include X-Request-ID and X-Correlation-ID."""
    response = await client.get("/health/live")
    assert "x-request-id" in response.headers
    assert "x-correlation-id" in response.headers


@pytest.mark.anyio
async def test_liveness_forwards_correlation_id(client):
    """If caller provides X-Correlation-ID, it should be echoed back."""
    cid = "test-correlation-12345"
    response = await client.get("/health/live", headers={"X-Correlation-ID": cid})
    assert response.headers["x-correlation-id"] == cid


@pytest.mark.anyio
async def test_liveness_includes_security_headers(client):
    """Health responses should still carry security headers."""
    response = await client.get("/health/live")
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"
    assert "strict-transport-security" in response.headers


@pytest.mark.anyio
async def test_readiness_returns_status(client):
    """GET /health/ready should return either 200 or 503 with checks dict.

    In test environment the DB may not be reachable, so we accept either
    status but verify the response structure.
    """
    response = await client.get("/health/ready")
    assert response.status_code in (200, 503)
    body = response.json()
    assert body["status"] in ("ok", "degraded")
    assert "timestamp" in body
    assert "checks" in body
    assert "database" in body["checks"]


@pytest.mark.anyio
async def test_unhandled_path_returns_404(client):
    """Unknown paths should return structured 404 JSON, not HTML."""
    response = await client.get("/nonexistent")
    assert response.status_code == 404
    body = response.json()
    assert body["error"] == "not_found"
    assert "request_id" in body
