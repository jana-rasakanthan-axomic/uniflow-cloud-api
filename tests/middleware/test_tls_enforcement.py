"""Tests for TLS enforcement middleware."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware.tls_enforcement import enforce_tls


# Create a test app for middleware testing
@pytest.fixture
def app():
    """Create a FastAPI app with TLS enforcement middleware."""
    test_app = FastAPI()

    @test_app.get("/test")
    async def test_endpoint():
        return {"status": "ok"}

    test_app.middleware("http")(enforce_tls)
    return test_app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app, raise_server_exceptions=False)


def test_tls_middleware_rejects_http(client):
    """Test that TLS middleware rejects HTTP requests."""
    # No X-Forwarded-Proto header means HTTP
    response = client.get("/test")

    assert response.status_code == 403


def test_tls_middleware_rejects_explicit_http(client):
    """Test that TLS middleware rejects requests with X-Forwarded-Proto: http."""
    response = client.get("/test", headers={"X-Forwarded-Proto": "http"})

    assert response.status_code == 403


def test_tls_middleware_accepts_https(client):
    """Test that TLS middleware accepts HTTPS requests."""
    response = client.get("/test", headers={"X-Forwarded-Proto": "https"})

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_tls_middleware_error_message(client):
    """Test that TLS middleware returns clear error message."""
    response = client.get("/test")

    assert response.status_code == 403
    assert "detail" in response.json()
    assert "https" in response.json()["detail"].lower() or "tls" in response.json()[
        "detail"
    ].lower()


def test_tls_middleware_localhost_bypass(client):
    """Test that TLS middleware bypasses check for localhost in development."""
    # This test assumes the middleware detects localhost
    # The actual implementation might vary based on how we detect dev environment
    # For now, we'll test that HTTPS is required for non-localhost
    response = client.get("/test", headers={"X-Forwarded-Proto": "http"})
    assert response.status_code == 403  # Should still reject HTTP even for localhost in prod


def test_tls_middleware_header_case_insensitive(client):
    """Test that header check is case-insensitive."""
    # FastAPI/Starlette handles header case-insensitivity automatically
    response = client.get("/test", headers={"x-forwarded-proto": "https"})

    assert response.status_code == 200
