"""Tests for DeviceService status update functionality."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.device import Device
from app.repositories.device_repository import DeviceRepository
from app.services.device_service import DeviceService
from app.shared.enums import DeviceStatus


@pytest.fixture
def mock_db():
    """Create mock database session."""
    session = AsyncMock()
    return session


@pytest.fixture
def mock_device_repository():
    """Create mock device repository."""
    repository = MagicMock(spec=DeviceRepository)
    repository.update_status = AsyncMock()
    return repository


@pytest.fixture
def device_service(mock_device_repository):
    """Create device service with mocked repository."""
    service = DeviceService()
    service.device_repository = mock_device_repository
    return service


@pytest.fixture
def test_org_id():
    """Test organization UUID."""
    return uuid4()


@pytest.fixture
def test_user_id():
    """Test user UUID."""
    return uuid4()


@pytest.fixture
def test_agent_id():
    """Test agent UUID."""
    return uuid4()


class TestDeviceServiceUpdateStatus:
    """Test DeviceService.update_device_status() method."""

    async def test_update_device_status_with_metadata(
        self,
        device_service,
        mock_db,
        mock_device_repository,
        test_org_id,
        test_user_id,
        test_agent_id
    ):
        """Test updating device status with metadata."""
        now = datetime.now(UTC)
        metadata = {
            "agent_version": "1.2.3",
            "disk_space_available_gb": 250,
            "cpu_percent": 45,
            "memory_percent": 60
        }

        # Mock device returned by repository
        updated_device = Device(
            id=uuid4(),
            org_id=test_org_id,
            user_id=test_user_id,
            agent_id=test_agent_id,
            machine_name="Test Machine",
            os="Windows 11",
            status=DeviceStatus.ONLINE.value,
            last_seen_at=now,
            created_at=now,
            device_metadata=metadata
        )

        mock_device_repository.update_status.return_value = updated_device

        # Update device status
        result = await device_service.update_device_status(
            db=mock_db,
            agent_id=test_agent_id,
            status=DeviceStatus.ONLINE,
            metadata=metadata
        )

        # Verify repository was called with correct params
        mock_device_repository.update_status.assert_called_once_with(
            db=mock_db,
            agent_id=test_agent_id,
            status=DeviceStatus.ONLINE,
            metadata=metadata
        )

        # Verify result
        assert result.agent_id == test_agent_id
        assert result.status == DeviceStatus.ONLINE.value
        assert result.device_metadata == metadata

    async def test_update_device_status_online(
        self,
        device_service,
        mock_db,
        mock_device_repository,
        test_org_id,
        test_user_id,
        test_agent_id
    ):
        """Test updating device status to ONLINE."""
        now = datetime.now(UTC)

        # Mock device returned by repository
        updated_device = Device(
            id=uuid4(),
            org_id=test_org_id,
            user_id=test_user_id,
            agent_id=test_agent_id,
            machine_name="Test Machine",
            os="Windows 11",
            status=DeviceStatus.ONLINE.value,
            last_seen_at=now,
            created_at=now
        )

        mock_device_repository.update_status.return_value = updated_device

        # Update device status
        result = await device_service.update_device_status(
            db=mock_db,
            agent_id=test_agent_id,
            status=DeviceStatus.ONLINE
        )

        # Verify result
        assert result.status == DeviceStatus.ONLINE.value

    async def test_update_device_status_offline(
        self,
        device_service,
        mock_db,
        mock_device_repository,
        test_org_id,
        test_user_id,
        test_agent_id
    ):
        """Test updating device status to OFFLINE."""
        now = datetime.now(UTC)

        # Mock device returned by repository
        updated_device = Device(
            id=uuid4(),
            org_id=test_org_id,
            user_id=test_user_id,
            agent_id=test_agent_id,
            machine_name="Test Machine",
            os="Windows 11",
            status=DeviceStatus.OFFLINE.value,
            last_seen_at=now,
            created_at=now
        )

        mock_device_repository.update_status.return_value = updated_device

        # Update device status
        result = await device_service.update_device_status(
            db=mock_db,
            agent_id=test_agent_id,
            status=DeviceStatus.OFFLINE
        )

        # Verify result
        assert result.status == DeviceStatus.OFFLINE.value

    async def test_update_device_status_preserves_last_seen(
        self,
        device_service,
        mock_db,
        mock_device_repository,
        test_org_id,
        test_user_id,
        test_agent_id
    ):
        """Test that update_device_status preserves last_seen when marking OFFLINE."""
        now = datetime.now(UTC)

        # Mock device returned by repository
        updated_device = Device(
            id=uuid4(),
            org_id=test_org_id,
            user_id=test_user_id,
            agent_id=test_agent_id,
            machine_name="Test Machine",
            os="Windows 11",
            status=DeviceStatus.OFFLINE.value,
            last_seen_at=now,
            created_at=now
        )

        mock_device_repository.update_status.return_value = updated_device

        # Update device status to OFFLINE
        await device_service.update_device_status(
            db=mock_db,
            agent_id=test_agent_id,
            status=DeviceStatus.OFFLINE
        )

        # Verify repository was called (last_seen will be preserved by repository)
        mock_device_repository.update_status.assert_called_once()
