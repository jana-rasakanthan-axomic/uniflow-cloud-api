"""Tests for device service."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from app.exceptions import InvalidSetupCodeError, SetupCodeAlreadyUsedError, SetupCodeExpiredError
from app.models.device import Device
from app.models.setup_code import SetupCode
from app.services.device_service import DeviceService, TokenPair


@pytest.fixture
def device_service():
    """Create device service instance."""
    return DeviceService()


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def test_org_id():
    """Test organization UUID."""
    return uuid4()


@pytest.fixture
def test_user_id():
    """Test user UUID."""
    return uuid4()


@pytest.fixture
def valid_setup_code(test_org_id):
    """Create a valid setup code."""
    return SetupCode(
        id=uuid4(),
        org_id=test_org_id,
        code="ABCD1234",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        used_at=None,
        created_at=datetime.now(UTC)
    )


class TestDeviceService:
    """Test device service for device linking."""

    async def test_link_device_success(
        self, device_service, mock_db_session, valid_setup_code
    ):
        """Test successful device linking creates device and returns tokens."""
        machine_info = {
            "machine_name": "John's MacBook Pro",
            "os": "macOS 14.2",
            "source_ip": "192.168.1.100"
        }

        # Mock the database query to return valid setup code
        with patch.object(
            device_service, "_validate_and_mark_used", return_value=valid_setup_code
        ):
            with patch.object(device_service, "_create_device") as mock_create_device:
                mock_device = Device(
                    id=uuid4(),
                    org_id=valid_setup_code.org_id,
                    user_id=uuid4(),
                    agent_id=uuid4(),
                    machine_name=machine_info["machine_name"],
                    os=machine_info["os"],
                    status="ONLINE",
                    created_at=datetime.now(UTC)
                )
                mock_create_device.return_value = mock_device

                with patch.object(device_service, "_create_refresh_token"):
                    with patch.object(device_service, "_generate_tokens") as mock_gen_tokens:
                        mock_gen_tokens.return_value = TokenPair(
                            agent_id=mock_device.agent_id,
                            access_token="access_token_here",
                            refresh_token="refresh_token_here"
                        )

                        with patch.object(device_service, "_log_success"):
                            result = await device_service.link_device(
                                db=mock_db_session,
                                setup_code="ABCD1234",
                                machine_info=machine_info
                            )

        # Verify result
        assert isinstance(result, TokenPair)
        assert result.agent_id == mock_device.agent_id
        assert result.access_token == "access_token_here"
        assert result.refresh_token == "refresh_token_here"

        # Verify commit was called
        mock_db_session.commit.assert_called_once()

    async def test_link_device_expired_code(
        self, device_service, mock_db_session, test_org_id
    ):
        """Test linking with expired code raises error and logs failure."""
        expired_code = SetupCode(
            id=uuid4(),
            org_id=test_org_id,
            code="ABCD1234",
            expires_at=datetime.now(UTC) - timedelta(hours=1),  # Expired
            used_at=None,
            created_at=datetime.now(UTC) - timedelta(days=7)
        )

        machine_info = {
            "machine_name": "Test Machine",
            "os": "Windows 11",
            "source_ip": "192.168.1.100"
        }

        # Mock to return expired code
        with patch.object(
            device_service, "_find_setup_code", return_value=expired_code
        ):
            with patch.object(device_service, "_log_failure") as mock_log_failure:
                with pytest.raises(SetupCodeExpiredError):
                    await device_service.link_device(
                        db=mock_db_session,
                        setup_code="ABCD1234",
                        machine_info=machine_info
                    )

                # Verify failure was logged
                mock_log_failure.assert_called_once()

    async def test_link_device_already_used_code(
        self, device_service, mock_db_session, test_org_id
    ):
        """Test linking with already used code raises error."""
        used_code = SetupCode(
            id=uuid4(),
            org_id=test_org_id,
            code="ABCD1234",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            used_at=datetime.now(UTC) - timedelta(hours=1),  # Already used
            created_at=datetime.now(UTC) - timedelta(days=7)
        )

        machine_info = {
            "machine_name": "Test Machine",
            "os": "Windows 11",
            "source_ip": "192.168.1.100"
        }

        with patch.object(
            device_service, "_find_setup_code", return_value=used_code
        ):
            with patch.object(device_service, "_log_failure"):
                with pytest.raises(SetupCodeAlreadyUsedError):
                    await device_service.link_device(
                        db=mock_db_session,
                        setup_code="ABCD1234",
                        machine_info=machine_info
                    )

    async def test_link_device_not_found_code(
        self, device_service, mock_db_session
    ):
        """Test linking with nonexistent code raises error."""
        machine_info = {
            "machine_name": "Test Machine",
            "os": "Windows 11",
            "source_ip": "192.168.1.100"
        }

        with patch.object(
            device_service, "_find_setup_code", return_value=None
        ):
            with patch.object(device_service, "_log_failure"):
                with pytest.raises(InvalidSetupCodeError):
                    await device_service.link_device(
                        db=mock_db_session,
                        setup_code="NOTFOUND",
                        machine_info=machine_info
                    )

    async def test_link_device_transaction_rollback_on_error(
        self, device_service, mock_db_session, valid_setup_code
    ):
        """Test that transaction is rolled back if device creation fails."""
        machine_info = {
            "machine_name": "Test Machine",
            "os": "Windows 11",
            "source_ip": "192.168.1.100"
        }

        with patch.object(
            device_service, "_validate_and_mark_used", return_value=valid_setup_code
        ):
            with patch.object(
                device_service, "_create_device", side_effect=Exception("DB Error")
            ):
                with pytest.raises(Exception, match="DB Error"):
                    await device_service.link_device(
                        db=mock_db_session,
                        setup_code="ABCD1234",
                        machine_info=machine_info
                    )

                # Verify rollback was called
                mock_db_session.rollback.assert_called_once()

    async def test_token_pair_dataclass(self):
        """Test TokenPair dataclass structure."""
        agent_id = uuid4()
        token_pair = TokenPair(
            agent_id=agent_id,
            access_token="access_token",
            refresh_token="refresh_token"
        )

        assert token_pair.agent_id == agent_id
        assert token_pair.access_token == "access_token"
        assert token_pair.refresh_token == "refresh_token"

    async def test_setup_code_partial_redaction(self, device_service):
        """Test that setup code is partially redacted in audit logs."""
        redacted = device_service._redact_setup_code("ABCD1234")
        assert redacted == "****1234"

    async def test_agent_id_is_uuid4(self, device_service, mock_db_session):
        """Test that generated agent_id is a valid UUID."""
        agent_id = device_service._generate_agent_id()
        assert isinstance(agent_id, UUID)
        # UUID4 has specific version bits
        assert agent_id.version == 4
