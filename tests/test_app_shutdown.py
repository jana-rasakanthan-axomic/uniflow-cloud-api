"""Tests for application shutdown behavior."""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_shutdown_handler_closes_all_connections():
    """Test that shutdown lifespan handler calls SignalingService.close_all_connections."""
    from app.main import app, lifespan

    # Create mock signaling service
    mock_signaling_service = AsyncMock()
    mock_signaling_service.close_all_connections = AsyncMock()

    # Patch SignalingService to return our mock
    with patch('app.main.SignalingService', return_value=mock_signaling_service):
        # Run lifespan context manager
        async with lifespan(app):
            pass  # Enter and immediately exit (triggering shutdown)

    # Verify close_all_connections was called
    mock_signaling_service.close_all_connections.assert_called_once()
