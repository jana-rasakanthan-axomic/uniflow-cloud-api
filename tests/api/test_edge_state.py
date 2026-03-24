"""Tests for POST /edge/state endpoint."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routers.edge import router as edge_router
from app.models.device import Device
from app.shared.enums import DeviceStatus


@pytest.fixture
def app():
    """Create FastAPI app for testing."""
    test_app = FastAPI()
    test_app.include_router(edge_router, prefix="/edge")
    return test_app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def test_agent_id():
    """Test agent UUID."""
    return uuid4()


@pytest.fixture
def test_org_id():
    """Test organization UUID."""
    return uuid4()


@pytest.fixture
def valid_jwt_token(test_agent_id, test_org_id):
    """Create valid JWT token for testing."""
    from app.services.jwt_service import JWTService

    jwt_service = JWTService()
    return jwt_service.create_access_token(
        agent_id=test_agent_id,
        org_id=test_org_id
    )


class TestEdgeStateEndpoint:
    """Test POST /edge/state endpoint."""

    @patch("app.api.routers.edge.get_db")
    @patch("app.api.routers.edge.get_agent_id_from_jwt")
    @patch("app.api.routers.edge.DeviceService")
    async def test_post_edge_state_online_success(
        self,
        mock_device_service_class,
        mock_get_agent_id,
        mock_get_db,
        client,
        test_agent_id,
        test_org_id,
        valid_jwt_token
    ):
        """Test POST /edge/state with ONLINE status returns success."""
        # Setup mocks
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        mock_get_agent_id.return_value = test_agent_id

        mock_device_service = MagicMock()
        mock_device = Device(
            id=uuid4(),
            org_id=test_org_id,
            user_id=uuid4(),
            agent_id=test_agent_id,
            machine_name="Test Machine",
            os="Windows 11",
            status=DeviceStatus.ONLINE.value,
            last_seen_at=datetime.now(UTC),
            created_at=datetime.now(UTC)
        )
        mock_device_service.update_device_status = AsyncMock(return_value=mock_device)
        mock_device_service_class.return_value = mock_device_service

        # Make request
        response = client.post(
            "/edge/state",
            json={"status": "ONLINE"},
            headers={"Authorization": f"Bearer {valid_jwt_token}"}
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["ack"] is True

    @patch("app.api.routers.edge.get_db")
    @patch("app.api.routers.edge.get_agent_id_from_jwt")
    @patch("app.api.routers.edge.DeviceService")
    async def test_post_edge_state_offline_success(
        self,
        mock_device_service_class,
        mock_get_agent_id,
        mock_get_db,
        client,
        test_agent_id,
        test_org_id,
        valid_jwt_token
    ):
        """Test POST /edge/state with OFFLINE status."""
        # Setup mocks
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        mock_get_agent_id.return_value = test_agent_id

        mock_device_service = MagicMock()
        mock_device = Device(
            id=uuid4(),
            org_id=test_org_id,
            user_id=uuid4(),
            agent_id=test_agent_id,
            machine_name="Test Machine",
            os="Windows 11",
            status=DeviceStatus.OFFLINE.value,
            last_seen_at=datetime.now(UTC),
            created_at=datetime.now(UTC)
        )
        mock_device_service.update_device_status = AsyncMock(return_value=mock_device)
        mock_device_service_class.return_value = mock_device_service

        # Make request
        response = client.post(
            "/edge/state",
            json={"status": "OFFLINE"},
            headers={"Authorization": f"Bearer {valid_jwt_token}"}
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["ack"] is True

    @patch("app.api.routers.edge.get_db")
    @patch("app.api.routers.edge.get_agent_id_from_jwt")
    @patch("app.api.routers.edge.DeviceService")
    async def test_post_edge_state_with_metadata(
        self,
        mock_device_service_class,
        mock_get_agent_id,
        mock_get_db,
        client,
        test_agent_id,
        test_org_id,
        valid_jwt_token
    ):
        """Test POST /edge/state with metadata."""
        # Setup mocks
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        mock_get_agent_id.return_value = test_agent_id

        metadata = {
            "agent_version": "1.2.3",
            "disk_space_available_gb": 250
        }

        mock_device_service = MagicMock()
        mock_device = Device(
            id=uuid4(),
            org_id=test_org_id,
            user_id=uuid4(),
            agent_id=test_agent_id,
            machine_name="Test Machine",
            os="Windows 11",
            status=DeviceStatus.ONLINE.value,
            last_seen_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
            device_metadata=metadata
        )
        mock_device_service.update_device_status = AsyncMock(return_value=mock_device)
        mock_device_service_class.return_value = mock_device_service

        # Make request
        response = client.post(
            "/edge/state",
            json={
                "status": "ONLINE",
                "metadata": metadata
            },
            headers={"Authorization": f"Bearer {valid_jwt_token}"}
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["ack"] is True

        # Verify metadata was passed to service
        mock_device_service.update_device_status.assert_called_once()
        call_args = mock_device_service.update_device_status.call_args
        assert call_args[1]["metadata"] == metadata

    async def test_post_edge_state_missing_auth(self, client):
        """Test POST /edge/state without JWT returns 401."""
        response = client.post(
            "/edge/state",
            json={"status": "ONLINE"}
        )

        # Should return 401 Unauthorized
        assert response.status_code in [401, 403]
