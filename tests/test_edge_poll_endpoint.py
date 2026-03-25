"""Tests for GET /poll endpoint."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import jwt
import pytest
from fastapi import HTTPException

from app.config import settings
from app.models.command import Command


@pytest.fixture
def agent_id() -> UUID:
    """Generate a test agent UUID."""
    return uuid4()


@pytest.fixture
def mock_db():
    """Mock database session."""
    return AsyncMock()


@pytest.fixture
def mock_signaling_service():
    """Mock SignalingService."""
    service = AsyncMock()
    service.hold_poll = AsyncMock(return_value=None)
    return service


@pytest.fixture
def create_jwt_token():
    """Factory for creating JWT tokens."""
    def _create_token(agent_id: UUID) -> str:
        payload = {
            "sub": str(agent_id),
            "exp": datetime.now(UTC).timestamp() + 3600
        }
        return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return _create_token


@pytest.mark.asyncio
async def test_poll_endpoint_returns_none_on_timeout(
    mock_db,
    agent_id: UUID,
    mock_signaling_service
):
    """Test poll endpoint returns action=none when no command available."""
    # Import here to avoid circular dependency issues
    from app.api.routers.edge import poll

    # Mock signaling service to return None (timeout)
    mock_signaling_service.hold_poll.return_value = None

    # Call endpoint directly
    from unittest.mock import patch
    with patch('app.api.routers.edge.SignalingService', return_value=mock_signaling_service):
        result = await poll(agent_id=agent_id, authenticated_agent_id=agent_id, db=mock_db)

    assert result["action"] == "none"


@pytest.mark.asyncio
async def test_poll_endpoint_returns_command_when_available(
    mock_db,
    agent_id: UUID,
    mock_signaling_service
):
    """Test poll endpoint returns command when available."""
    from app.api.routers.edge import poll

    # Create mock command
    mock_command = MagicMock(spec=Command)
    mock_command.type = "SCAN"
    mock_command.payload_json = {"path": "/test/path"}

    # Mock signaling service to return command
    mock_signaling_service.hold_poll.return_value = mock_command

    # Call endpoint
    from unittest.mock import patch
    with patch('app.api.routers.edge.SignalingService', return_value=mock_signaling_service):
        result = await poll(agent_id=agent_id, authenticated_agent_id=agent_id, db=mock_db)

    assert result["action"] == "SCAN"
    assert result["payload"] == {"path": "/test/path"}


@pytest.mark.asyncio
async def test_poll_endpoint_validates_agent_id_matches_jwt(
    mock_db,
    agent_id: UUID,
):
    """Test poll validates that query param agent_id matches JWT claim."""
    from app.api.routers.edge import poll

    different_agent_id = uuid4()

    # Call with mismatched agent IDs
    with pytest.raises(HTTPException) as exc_info:
        await poll(agent_id=agent_id, authenticated_agent_id=different_agent_id, db=mock_db)

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_poll_endpoint_calls_hold_poll_with_correct_params(
    mock_db,
    agent_id: UUID,
    mock_signaling_service
):
    """Test poll endpoint calls SignalingService.hold_poll with correct parameters."""
    from app.api.routers.edge import poll

    mock_signaling_service.hold_poll.return_value = None

    # Call endpoint
    from unittest.mock import patch
    with patch('app.api.routers.edge.SignalingService', return_value=mock_signaling_service):
        with patch('app.api.routers.edge.settings') as mock_settings:
            mock_settings.poll_timeout_seconds = 42
            await poll(agent_id=agent_id, authenticated_agent_id=agent_id, db=mock_db)

    # Verify hold_poll was called with correct args
    mock_signaling_service.hold_poll.assert_called_once_with(
        mock_db,
        agent_id,
        timeout=42
    )
