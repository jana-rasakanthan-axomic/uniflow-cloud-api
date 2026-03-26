"""Tests for SignalingService stale detection functionality."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.device import Device
from app.repositories.device_repository import DeviceRepository
from app.services.signaling_service import SignalingService
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
    repository.find_stale = AsyncMock()
    repository.update_status = AsyncMock()
    return repository


@pytest.fixture
def signaling_service(mock_device_repository):
    """Create signaling service with mocked repository."""
    service = SignalingService()
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


class TestSignalingServiceCheckStale:
    """Test SignalingService.check_stale_agents() method."""

    async def test_check_stale_agents_marks_offline(
        self,
        signaling_service,
        mock_db,
        mock_device_repository,
        test_org_id,
        test_user_id
    ):
        """Test that check_stale_agents marks stale devices OFFLINE."""
        now = datetime.now(UTC)

        # Create stale devices
        stale_device_1 = Device(
            id=uuid4(),
            org_id=test_org_id,
            user_id=test_user_id,
            agent_id=uuid4(),
            machine_name="Stale Machine 1",
            os="Windows 11",
            status=DeviceStatus.ONLINE.value,
            last_seen_at=now - timedelta(seconds=120),
            created_at=now
        )

        stale_device_2 = Device(
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

        # Mock repository to return stale devices
        mock_device_repository.find_stale.return_value = [stale_device_1, stale_device_2]

        # Check stale agents
        count = await signaling_service.check_stale_agents(db=mock_db)

        # Verify find_stale was called with correct threshold
        mock_device_repository.find_stale.assert_called_once_with(
            db=mock_db,
            threshold_seconds=110,
            exclude_agent_ids=set()
        )

        # Verify both devices were marked OFFLINE
        assert mock_device_repository.update_status.call_count == 2

        # Verify count returned
        assert count == 2

    async def test_check_stale_agents_respects_active_polls(
        self,
        signaling_service,
        mock_db,
        mock_device_repository,
        test_org_id,
        test_user_id
    ):
        """Test that check_stale_agents excludes agents with active long-poll connections."""
        now = datetime.now(UTC)

        # Create stale device with active poll
        active_agent_id = uuid4()

        # Create stale device without active poll
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

        # Add active agent to tracking set
        signaling_service.active_poll_agent_ids.add(active_agent_id)

        # Mock repository to return only non-active device
        mock_device_repository.find_stale.return_value = [stale_device]

        # Check stale agents
        count = await signaling_service.check_stale_agents(db=mock_db)

        # Verify find_stale was called with excluded agent_id
        mock_device_repository.find_stale.assert_called_once_with(
            db=mock_db,
            threshold_seconds=110,
            exclude_agent_ids={active_agent_id}
        )

        # Verify only non-active device was marked OFFLINE
        assert mock_device_repository.update_status.call_count == 1
        assert count == 1

    async def test_check_stale_agents_returns_count(
        self,
        signaling_service,
        mock_db,
        mock_device_repository,
        test_org_id,
        test_user_id
    ):
        """Test that check_stale_agents returns count of agents marked stale."""
        now = datetime.now(UTC)

        # Create 3 stale devices
        stale_devices = [
            Device(
                id=uuid4(),
                org_id=test_org_id,
                user_id=test_user_id,
                agent_id=uuid4(),
                machine_name=f"Stale Machine {i}",
                os="Windows 11",
                status=DeviceStatus.ONLINE.value,
                last_seen_at=now - timedelta(seconds=120 + i),
                created_at=now
            )
            for i in range(3)
        ]

        # Mock repository to return stale devices
        mock_device_repository.find_stale.return_value = stale_devices

        # Check stale agents
        count = await signaling_service.check_stale_agents(db=mock_db)

        # Verify count matches number of devices
        assert count == 3

    async def test_check_stale_agents_no_stale_devices(
        self,
        signaling_service,
        mock_db,
        mock_device_repository
    ):
        """Test that check_stale_agents returns 0 when no stale devices exist."""
        # Mock repository to return empty list
        mock_device_repository.find_stale.return_value = []

        # Check stale agents
        count = await signaling_service.check_stale_agents(db=mock_db)

        # Verify count is 0
        assert count == 0

        # Verify update_status was not called
        mock_device_repository.update_status.assert_not_called()

    async def test_check_stale_agents_preserves_last_seen(
        self,
        signaling_service,
        mock_db,
        mock_device_repository,
        test_org_id,
        test_user_id
    ):
        """Test that check_stale_agents preserves original last_seen_at timestamp."""
        now = datetime.now(UTC)
        original_last_seen = now - timedelta(seconds=120)

        # Create stale device
        stale_device = Device(
            id=uuid4(),
            org_id=test_org_id,
            user_id=test_user_id,
            agent_id=uuid4(),
            machine_name="Stale Machine",
            os="Windows 11",
            status=DeviceStatus.ONLINE.value,
            last_seen_at=original_last_seen,
            created_at=now
        )

        # Mock repository
        mock_device_repository.find_stale.return_value = [stale_device]

        # Check stale agents
        await signaling_service.check_stale_agents(db=mock_db)

        # Verify update_status was called with preserved timestamp
        mock_device_repository.update_status.assert_called_once_with(
            db=mock_db,
            agent_id=stale_device.agent_id,
            status=DeviceStatus.OFFLINE,
            last_seen=original_last_seen
        )


class TestSignalingServiceActivePolls:
    """Test SignalingService active poll tracking."""

    def test_active_poll_agent_ids_initialization(self, signaling_service):
        """Test that active_poll_agent_ids is initialized as empty set."""
        assert isinstance(signaling_service.active_poll_agent_ids, set)
        assert len(signaling_service.active_poll_agent_ids) == 0

    def test_add_active_poll_agent(self, signaling_service):
        """Test adding an agent to active poll tracking."""
        agent_id = uuid4()
        signaling_service.active_poll_agent_ids.add(agent_id)

        assert agent_id in signaling_service.active_poll_agent_ids
        assert len(signaling_service.active_poll_agent_ids) == 1

    def test_remove_active_poll_agent(self, signaling_service):
        """Test removing an agent from active poll tracking."""
        agent_id = uuid4()
        signaling_service.active_poll_agent_ids.add(agent_id)
        signaling_service.active_poll_agent_ids.remove(agent_id)

        assert agent_id not in signaling_service.active_poll_agent_ids
        assert len(signaling_service.active_poll_agent_ids) == 0
