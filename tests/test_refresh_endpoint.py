"""Tests for POST /auth/tokens/refresh endpoint."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import jwt
import pytest
from httpx import AsyncClient, ASGITransport

from app.config import settings
from app.exceptions import InvalidTokenError, RevokedTokenError
from app.main import app
from app.services.device_service import TokenPair


@pytest.fixture
def test_agent_id():
    """Test agent UUID."""
    return uuid4()


@pytest.fixture
def test_org_id():
    """Test organization UUID."""
    return uuid4()


@pytest.fixture
def test_chain_id():
    """Test token chain UUID."""
    return uuid4()


@pytest.fixture
def valid_refresh_token_jwt(test_agent_id, test_org_id, test_chain_id):
    """Create a valid refresh token JWT."""
    now = datetime.now(UTC)
    expires_at = now + timedelta(days=90)

    claims = {
        "sub": str(test_agent_id),
        "org_id": str(test_org_id),
        "chain_id": str(test_chain_id),
        "sequence_num": 1,
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp())
    }

    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)


class TestRefreshEndpoint:
    """Test POST /auth/tokens/refresh endpoint."""

    @pytest.mark.asyncio
    async def test_refresh_success(
        self,
        valid_refresh_token_jwt,
        test_agent_id
    ):
        """Test successful token refresh returns 200 with new token pair."""
        # Mock the device service
        with patch("app.api.routers.auth.DeviceService") as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.refresh_tokens = AsyncMock(return_value=TokenPair(
                agent_id=test_agent_id,
                access_token="new_access_token",
                refresh_token="new_refresh_token"
            ))

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/auth/tokens/refresh",
                    json={"refresh_token": valid_refresh_token_jwt}
                )

            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["access_token"] == "new_access_token"
            assert data["refresh_token"] == "new_refresh_token"

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self):
        """Test that invalid token returns 401."""
        with patch("app.api.routers.auth.DeviceService") as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.refresh_tokens = AsyncMock(side_effect=InvalidTokenError("Invalid token"))

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/auth/tokens/refresh",
                    json={"refresh_token": "invalid.token.here"}
                )

            assert response.status_code == 401
            assert "detail" in response.json()

    @pytest.mark.asyncio
    async def test_refresh_revoked_token(
        self,
        valid_refresh_token_jwt
    ):
        """Test that revoked token returns 403."""
        with patch("app.api.routers.auth.DeviceService") as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.refresh_tokens = AsyncMock(side_effect=RevokedTokenError("Token revoked"))

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/auth/tokens/refresh",
                    json={"refresh_token": valid_refresh_token_jwt}
                )

            assert response.status_code == 403
            assert "detail" in response.json()

    @pytest.mark.asyncio
    async def test_refresh_missing_token(self):
        """Test that missing refresh_token returns 422."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/tokens/refresh",
                json={}
            )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_refresh_empty_token(self):
        """Test that empty refresh_token returns 422."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/tokens/refresh",
                json={"refresh_token": ""}
            )

        assert response.status_code == 422
