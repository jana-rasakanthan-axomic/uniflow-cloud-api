"""Tests for DeviceService.refresh_tokens() method."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import jwt
import pytest

from app.config import settings
from app.exceptions import InvalidTokenError, RevokedTokenError
from app.models.device import Device
from app.models.refresh_token import RefreshToken
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
    session.begin = MagicMock()
    # Make session.begin() return a context manager
    session.begin.return_value.__aenter__ = AsyncMock()
    session.begin.return_value.__aexit__ = AsyncMock()
    return session


@pytest.fixture
def test_agent_id():
    """Test agent UUID."""
    return uuid4()


@pytest.fixture
def test_org_id():
    """Test organization UUID."""
    return uuid4()


@pytest.fixture
def test_user_id():
    """Test user UUID."""
    return uuid4()


@pytest.fixture
def test_device_id():
    """Test device UUID."""
    return uuid4()


@pytest.fixture
def test_chain_id():
    """Test token chain UUID."""
    return uuid4()


@pytest.fixture
def valid_refresh_token_jwt(device_service, test_agent_id, test_org_id, test_chain_id):
    """Create a valid refresh token JWT."""
    return device_service.jwt_service.create_refresh_token(
        agent_id=test_agent_id,
        org_id=test_org_id,
        chain_id=test_chain_id,
        sequence_num=1
    )


@pytest.fixture
def mock_refresh_token_record(test_user_id, test_device_id, test_chain_id):
    """Create a mock RefreshToken record."""
    return RefreshToken(
        id=uuid4(),
        user_id=test_user_id,
        device_id=test_device_id,
        token_hash="token_hash_value",
        chain_id=test_chain_id,
        sequence_num=1,
        revoked_at=None,
        expires_at=datetime.now(UTC) + timedelta(days=90),
        created_at=datetime.now(UTC)
    )


class TestDeviceServiceRefresh:
    """Test DeviceService token refresh functionality."""

    @pytest.mark.asyncio
    async def test_refresh_tokens_success(
        self,
        device_service,
        mock_db_session,
        valid_refresh_token_jwt,
        mock_refresh_token_record,
        test_agent_id,
        test_org_id
    ):
        """Test successful token refresh returns new token pair."""
        source_ip = "192.168.1.100"

        # Mock the repository instance on the service
        device_service.token_repository.find_by_token_hash = AsyncMock(return_value=mock_refresh_token_record)
        device_service.token_repository.revoke = AsyncMock()
        device_service.token_repository.create = AsyncMock(return_value=mock_refresh_token_record)

        result = await device_service.refresh_tokens(
            db=mock_db_session,
            refresh_token=valid_refresh_token_jwt,
            source_ip=source_ip
        )

        # Verify result is a TokenPair
        assert isinstance(result, TokenPair)
        assert result.agent_id == test_agent_id
        assert isinstance(result.access_token, str)
        assert isinstance(result.refresh_token, str)
        assert len(result.access_token) > 0
        assert len(result.refresh_token) > 0

        # Verify old token was revoked
        device_service.token_repository.revoke.assert_called_once()

        # Verify new token was created with incremented sequence
        device_service.token_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_tokens_increments_sequence(
        self,
        device_service,
        mock_db_session,
        valid_refresh_token_jwt,
        mock_refresh_token_record
    ):
        """Test that new refresh token has incremented sequence_num."""
        source_ip = "192.168.1.100"

        device_service.token_repository.find_by_token_hash = AsyncMock(return_value=mock_refresh_token_record)
        device_service.token_repository.revoke = AsyncMock()

        # Capture the token that was created
        created_token = None
        async def capture_create(db, token):
            nonlocal created_token
            created_token = token
            return token
        device_service.token_repository.create = AsyncMock(side_effect=capture_create)

        await device_service.refresh_tokens(
            db=mock_db_session,
            refresh_token=valid_refresh_token_jwt,
            source_ip=source_ip
        )

        # Verify new token has sequence_num = old + 1
        assert created_token is not None
        assert created_token.sequence_num == mock_refresh_token_record.sequence_num + 1

    @pytest.mark.asyncio
    async def test_refresh_tokens_invalid_jwt(
        self,
        device_service,
        mock_db_session
    ):
        """Test that invalid JWT raises InvalidTokenError."""
        invalid_token = "not.a.valid.jwt"
        source_ip = "192.168.1.100"

        with pytest.raises(InvalidTokenError):
            await device_service.refresh_tokens(
                db=mock_db_session,
                refresh_token=invalid_token,
                source_ip=source_ip
            )

    @pytest.mark.asyncio
    async def test_refresh_tokens_expired_jwt(
        self,
        device_service,
        mock_db_session,
        test_agent_id,
        test_org_id,
        test_chain_id
    ):
        """Test that expired JWT raises InvalidTokenError."""
        # Create an expired token
        past_time = datetime.now(UTC) - timedelta(days=100)
        claims = {
            "sub": str(test_agent_id),
            "org_id": str(test_org_id),
            "chain_id": str(test_chain_id),
            "sequence_num": 1,
            "type": "refresh",
            "iat": int(past_time.timestamp()),
            "exp": int((past_time + timedelta(days=1)).timestamp())
        }
        expired_token = jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)

        source_ip = "192.168.1.100"

        with pytest.raises(InvalidTokenError):
            await device_service.refresh_tokens(
                db=mock_db_session,
                refresh_token=expired_token,
                source_ip=source_ip
            )

    @pytest.mark.asyncio
    async def test_refresh_tokens_not_in_database(
        self,
        device_service,
        mock_db_session,
        valid_refresh_token_jwt
    ):
        """Test that token not in database raises InvalidTokenError."""
        source_ip = "192.168.1.100"

        # Return None to simulate token not found in DB
        device_service.token_repository.find_by_token_hash = AsyncMock(return_value=None)

        with pytest.raises(InvalidTokenError):
            await device_service.refresh_tokens(
                db=mock_db_session,
                refresh_token=valid_refresh_token_jwt,
                source_ip=source_ip
            )

    @pytest.mark.asyncio
    async def test_refresh_tokens_reuse_detected(
        self,
        device_service,
        mock_db_session,
        valid_refresh_token_jwt,
        mock_refresh_token_record
    ):
        """Test that presenting a revoked token raises RevokedTokenError."""
        source_ip = "192.168.1.100"

        # Make the token already revoked
        mock_refresh_token_record.revoked_at = datetime.now(UTC)

        device_service.token_repository.find_by_token_hash = AsyncMock(return_value=mock_refresh_token_record)
        device_service.token_repository.revoke_chain = AsyncMock(return_value=3)

        with pytest.raises(RevokedTokenError):
            await device_service.refresh_tokens(
                db=mock_db_session,
                refresh_token=valid_refresh_token_jwt,
                source_ip=source_ip
            )

    @pytest.mark.asyncio
    async def test_reuse_revokes_chain_and_logs(
        self,
        device_service,
        mock_db_session,
        valid_refresh_token_jwt,
        mock_refresh_token_record
    ):
        """Test that reuse detection revokes entire chain and logs audit event."""
        source_ip = "192.168.1.100"

        # Make the token already revoked
        mock_refresh_token_record.revoked_at = datetime.now(UTC)

        device_service.token_repository.find_by_token_hash = AsyncMock(return_value=mock_refresh_token_record)
        device_service.token_repository.revoke_chain = AsyncMock(return_value=3)

        with patch.object(device_service.audit_service, "log_event") as mock_log:
            with pytest.raises(RevokedTokenError):
                await device_service.refresh_tokens(
                    db=mock_db_session,
                    refresh_token=valid_refresh_token_jwt,
                    source_ip=source_ip
                )

            # Verify chain was revoked
            device_service.token_repository.revoke_chain.assert_called_once_with(
                mock_db_session,
                mock_refresh_token_record.chain_id
            )

            # Verify audit log was written
            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert call_args[1]["event_type"] == "REFRESH_REUSE_DETECTED"
            assert call_args[1]["source_ip"] == source_ip
