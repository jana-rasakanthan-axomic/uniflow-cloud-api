"""Integration tests for POST /auth/device/link endpoint."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.routers.auth import router as auth_router
from app.exceptions import InvalidSetupCodeError, SetupCodeAlreadyUsedError, SetupCodeExpiredError
from app.services.device_service import TokenPair


# Create a test app
@pytest.fixture
def app():
    """Create FastAPI app for testing."""
    from app.middleware.rate_limit_dependency import check_device_link_rate_limit

    test_app = FastAPI()
    test_app.include_router(auth_router, prefix="/auth")

    # Override rate limit dependency for tests
    async def no_rate_limit():
        pass

    test_app.dependency_overrides[check_device_link_rate_limit] = no_rate_limit

    return test_app


@pytest.fixture
async def client(app):
    """Create async HTTP client for testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestDeviceLinkEndpoint:
    """Test POST /auth/device/link endpoint."""

    async def test_device_link_success(self, client):
        """Test successful device link returns 200 with tokens."""
        request_data = {
            "setup_code": "ABCD1234",
            "machine_name": "John's MacBook Pro",
            "os": "macOS 14.2"
        }

        agent_id = uuid4()
        mock_token_pair = TokenPair(
            agent_id=agent_id,
            access_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.access",
            refresh_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.refresh"
        )

        with patch("app.api.routers.auth.DeviceService") as mock_device_service:
            mock_service = mock_device_service.return_value
            mock_service.link_device = AsyncMock(return_value=mock_token_pair)

            response = await client.post("/auth/device/link", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert "agent_id" in data
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["access_token"] == mock_token_pair.access_token
        assert data["refresh_token"] == mock_token_pair.refresh_token

    async def test_device_link_invalid_code(self, client):
        """Test invalid setup code returns 401."""
        request_data = {
            "setup_code": "INVALID1",
            "machine_name": "Test Machine",
            "os": "Windows 11"
        }

        with patch("app.api.routers.auth.DeviceService") as mock_device_service:
            mock_service = mock_device_service.return_value
            mock_service.link_device = AsyncMock(
                side_effect=InvalidSetupCodeError("Invalid code")
            )

            response = await client.post("/auth/device/link", json=request_data)

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "Invalid or expired setup code" in data["detail"]

    async def test_device_link_expired_code(self, client):
        """Test expired setup code returns 401."""
        request_data = {
            "setup_code": "ABCD1234",
            "machine_name": "Test Machine",
            "os": "Windows 11"
        }

        with patch("app.api.routers.auth.DeviceService") as mock_device_service:
            mock_service = mock_device_service.return_value
            mock_service.link_device = AsyncMock(
                side_effect=SetupCodeExpiredError("Expired")
            )

            response = await client.post("/auth/device/link", json=request_data)

        assert response.status_code == 401
        data = response.json()
        assert "Invalid or expired setup code" in data["detail"]

    async def test_device_link_used_code(self, client):
        """Test already used setup code returns 410."""
        request_data = {
            "setup_code": "ABCD1234",
            "machine_name": "Test Machine",
            "os": "Windows 11"
        }

        with patch("app.api.routers.auth.DeviceService") as mock_device_service:
            mock_service = mock_device_service.return_value
            mock_service.link_device = AsyncMock(
                side_effect=SetupCodeAlreadyUsedError("Already used")
            )

            response = await client.post("/auth/device/link", json=request_data)

        assert response.status_code == 410
        data = response.json()
        assert "Setup code already used" in data["detail"]

    async def test_device_link_malformed_request(self, client):
        """Test malformed request returns 422 validation error."""
        # Missing required field
        request_data = {
            "setup_code": "ABCD1234",
            "machine_name": "Test Machine"
            # Missing 'os' field
        }

        response = await client.post("/auth/device/link", json=request_data)

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    async def test_device_link_invalid_setup_code_format(self, client):
        """Test invalid setup code format returns 422."""
        # Setup code too short
        request_data = {
            "setup_code": "ABC123",  # Only 6 chars
            "machine_name": "Test Machine",
            "os": "Windows 11"
        }

        response = await client.post("/auth/device/link", json=request_data)

        assert response.status_code == 422

    async def test_device_link_setup_code_not_uppercase(self, client):
        """Test lowercase setup code returns 422."""
        request_data = {
            "setup_code": "abcd1234",  # Lowercase
            "machine_name": "Test Machine",
            "os": "Windows 11"
        }

        response = await client.post("/auth/device/link", json=request_data)

        assert response.status_code == 422

    async def test_device_link_machine_name_too_long(self, client):
        """Test machine name exceeding 255 chars returns 422."""
        request_data = {
            "setup_code": "ABCD1234",
            "machine_name": "A" * 256,  # Too long
            "os": "Windows 11"
        }

        response = await client.post("/auth/device/link", json=request_data)

        assert response.status_code == 422

    async def test_device_link_os_too_long(self, client):
        """Test OS field exceeding 100 chars returns 422."""
        request_data = {
            "setup_code": "ABCD1234",
            "machine_name": "Test Machine",
            "os": "A" * 101  # Too long
        }

        response = await client.post("/auth/device/link", json=request_data)

        assert response.status_code == 422

    async def test_device_link_extracts_source_ip_from_x_forwarded_for(self, client):
        """Test source IP is extracted from X-Forwarded-For header."""
        request_data = {
            "setup_code": "ABCD1234",
            "machine_name": "Test Machine",
            "os": "Windows 11"
        }

        agent_id = uuid4()
        mock_token_pair = TokenPair(
            agent_id=agent_id,
            access_token="access_token",
            refresh_token="refresh_token"
        )

        with patch("app.api.routers.auth.DeviceService") as mock_device_service:
            mock_service = mock_device_service.return_value
            mock_service.link_device = AsyncMock(return_value=mock_token_pair)

            response = await client.post(
                "/auth/device/link",
                json=request_data,
                headers={"X-Forwarded-For": "203.0.113.195, 192.0.2.1"}
            )

        assert response.status_code == 200

        # Verify link_device was called with correct source_ip
        call_args = mock_service.link_device.call_args
        machine_info = call_args.kwargs["machine_info"]
        assert machine_info["source_ip"] == "203.0.113.195"  # First IP in list

    async def test_device_link_uses_client_host_when_no_x_forwarded_for(self, client):
        """Test source IP falls back to client.host when header missing."""
        request_data = {
            "setup_code": "ABCD1234",
            "machine_name": "Test Machine",
            "os": "Windows 11"
        }

        agent_id = uuid4()
        mock_token_pair = TokenPair(
            agent_id=agent_id,
            access_token="access_token",
            refresh_token="refresh_token"
        )

        with patch("app.api.routers.auth.DeviceService") as mock_device_service:
            mock_service = mock_device_service.return_value
            mock_service.link_device = AsyncMock(return_value=mock_token_pair)

            response = await client.post("/auth/device/link", json=request_data)

        assert response.status_code == 200

        # Verify link_device was called
        call_args = mock_service.link_device.call_args
        machine_info = call_args.kwargs["machine_info"]
        # In test environment, this will be the test client IP
        assert "source_ip" in machine_info
