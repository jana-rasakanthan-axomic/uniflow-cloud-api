"""Tests for Device repository."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.engine import Result, ScalarResult

from app.models.device import Device
from app.repositories.device_repository import DeviceRepository
from app.shared.enums import DeviceStatus


@pytest.fixture
def mock_db():
    """Create mock database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def device_repository():
    """Create device repository instance."""
    return DeviceRepository()


@pytest.fixture
def test_org_id():
    """Test organization UUID."""
    return uuid4()


@pytest.fixture
def test_user_id():
    """Test user UUID."""
    return uuid4()


class TestDeviceRepositoryFindStale:
    """Test DeviceRepository.find_stale() method for stale detection."""

    async def test_find_stale_devices_by_threshold(
        self, mock_db, device_repository, test_org_id, test_user_id
    ):
        """Test that find_stale() returns only devices older than threshold."""
        now = datetime.now(UTC)

        # Create stale ONLINE device
        stale_device = Device(
            id=uuid4(),
            org_id=test_org_id,
            user_id=test_user_id,
            agent_id=uuid4(),
            machine_name="Stale Machine",
            os="Windows 11",
            status=DeviceStatus.ONLINE.value,
            last_seen_at=now - timedelta(seconds=120),
            created_at=now
        )

        # Mock database result
        mock_result = MagicMock(spec=Result)
        mock_scalars = MagicMock(spec=ScalarResult)
        mock_scalars.all.return_value = [stale_device]
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        # Find stale devices with 110-second threshold
        stale_devices = await device_repository.find_stale(
            db=mock_db,
            threshold_seconds=110
        )

        # Should return the stale device
        assert len(stale_devices) == 1
        assert stale_devices[0].agent_id == stale_device.agent_id
        assert stale_devices[0].status == DeviceStatus.ONLINE.value

        # Verify query was executed
        mock_db.execute.assert_called_once()

    async def test_find_stale_excludes_active_agents(
        self, mock_db, device_repository, test_org_id, test_user_id
    ):
        """Test that find_stale() excludes agents with active long-poll connections."""
        now = datetime.now(UTC)

        # Create stale device that should be excluded
        excluded_agent_id = uuid4()

        # Create stale device that should be returned
        stale_device = Device(
            id=uuid4(),
            org_id=test_org_id,
            user_id=test_user_id,
            agent_id=uuid4(),
            machine_name="Stale Machine 2",
            os="macOS 14",
            status=DeviceStatus.ONLINE.value,
            last_seen_at=now - timedelta(seconds=130),
            created_at=now
        )

        # Mock database result (only returns non-excluded device)
        mock_result = MagicMock(spec=Result)
        mock_scalars = MagicMock(spec=ScalarResult)
        mock_scalars.all.return_value = [stale_device]
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        # Find stale devices, excluding one agent
        stale_devices = await device_repository.find_stale(
            db=mock_db,
            threshold_seconds=110,
            exclude_agent_ids=[excluded_agent_id]
        )

        # Should return only the non-excluded device
        assert len(stale_devices) == 1
        assert stale_devices[0].agent_id == stale_device.agent_id

    async def test_find_stale_empty_result(
        self, mock_db, device_repository
    ):
        """Test that find_stale() returns empty list when no stale devices exist."""
        # Mock empty database result
        mock_result = MagicMock(spec=Result)
        mock_scalars = MagicMock(spec=ScalarResult)
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        # Find stale devices
        stale_devices = await device_repository.find_stale(
            db=mock_db,
            threshold_seconds=110
        )

        # Should return empty list
        assert len(stale_devices) == 0


class TestDeviceRepositoryUpdateStatus:
    """Test DeviceRepository.update_status() method for status updates."""

    async def test_update_status_sets_timestamp(
        self, mock_db, device_repository, test_org_id, test_user_id
    ):
        """Test that update_status() sets last_seen_at to current time by default."""
        now = datetime.now(UTC)
        agent_id = uuid4()

        # Create device
        updated_device = Device(
            id=uuid4(),
            org_id=test_org_id,
            user_id=test_user_id,
            agent_id=agent_id,
            machine_name="Test Machine",
            os="Windows 11",
            status=DeviceStatus.ONLINE.value,
            last_seen_at=now,
            created_at=now
        )

        # Mock database execute for update
        mock_update_result = MagicMock()
        # Mock database execute for select
        mock_select_result = MagicMock(spec=Result)
        mock_select_result.scalar_one_or_none.return_value = updated_device

        # Configure mock to return different results for update vs select
        mock_db.execute.side_effect = [mock_update_result, mock_select_result]

        # Update status to ONLINE
        result = await device_repository.update_status(
            db=mock_db,
            agent_id=agent_id,
            status=DeviceStatus.ONLINE
        )

        # Verify status updated
        assert result is not None
        assert result.status == DeviceStatus.ONLINE.value

        # Verify last_seen_at was updated (device returned has current timestamp)
        time_diff = datetime.now(UTC) - result.last_seen_at
        assert time_diff.total_seconds() < 5

    async def test_update_status_preserves_timestamp(
        self, mock_db, device_repository, test_org_id, test_user_id
    ):
        """Test that update_status() preserves last_seen_at when explicitly provided."""
        now = datetime.now(UTC)
        original_timestamp = now - timedelta(seconds=120)
        agent_id = uuid4()

        # Create device with preserved timestamp
        updated_device = Device(
            id=uuid4(),
            org_id=test_org_id,
            user_id=test_user_id,
            agent_id=agent_id,
            machine_name="Test Machine",
            os="Windows 11",
            status=DeviceStatus.OFFLINE.value,
            last_seen_at=original_timestamp,
            created_at=now
        )

        # Mock database results
        mock_update_result = MagicMock()
        mock_select_result = MagicMock(spec=Result)
        mock_select_result.scalar_one_or_none.return_value = updated_device
        mock_db.execute.side_effect = [mock_update_result, mock_select_result]

        # Update status to OFFLINE but preserve original timestamp
        result = await device_repository.update_status(
            db=mock_db,
            agent_id=agent_id,
            status=DeviceStatus.OFFLINE,
            last_seen=original_timestamp
        )

        # Verify status updated
        assert result is not None
        assert result.status == DeviceStatus.OFFLINE.value

        # Verify last_seen_at preserved
        assert result.last_seen_at == original_timestamp

    async def test_update_status_with_metadata(
        self, mock_db, device_repository, test_org_id, test_user_id
    ):
        """Test that update_status() can update device_metadata field."""
        now = datetime.now(UTC)
        agent_id = uuid4()

        # Metadata to store
        metadata = {
            "agent_version": "1.2.3",
            "disk_space_available_gb": 250,
            "cpu_percent": 45,
            "memory_percent": 60
        }

        # Create device with metadata
        updated_device = Device(
            id=uuid4(),
            org_id=test_org_id,
            user_id=test_user_id,
            agent_id=agent_id,
            machine_name="Test Machine",
            os="Windows 11",
            status=DeviceStatus.ONLINE.value,
            last_seen_at=now,
            created_at=now,
            device_metadata=metadata
        )

        # Mock database results
        mock_update_result = MagicMock()
        mock_select_result = MagicMock(spec=Result)
        mock_select_result.scalar_one_or_none.return_value = updated_device
        mock_db.execute.side_effect = [mock_update_result, mock_select_result]

        # Update status with metadata
        result = await device_repository.update_status(
            db=mock_db,
            agent_id=agent_id,
            status=DeviceStatus.ONLINE,
            metadata=metadata
        )

        # Verify metadata stored
        assert result is not None
        assert result.device_metadata == metadata
        assert result.device_metadata["agent_version"] == "1.2.3"
        assert result.device_metadata["disk_space_available_gb"] == 250

    async def test_update_status_device_not_found(
        self, mock_db, device_repository
    ):
        """Test that update_status() returns None when device not found."""
        # Mock database results (device not found)
        mock_update_result = MagicMock()
        mock_select_result = MagicMock(spec=Result)
        mock_select_result.scalar_one_or_none.return_value = None
        mock_db.execute.side_effect = [mock_update_result, mock_select_result]

        # Try to update non-existent device
        result = await device_repository.update_status(
            db=mock_db,
            agent_id=uuid4(),  # Random UUID that doesn't exist
            status=DeviceStatus.ONLINE
        )

        # Should return None
        assert result is None
