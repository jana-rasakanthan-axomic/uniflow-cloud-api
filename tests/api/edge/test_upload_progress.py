"""Tests for POST /edge/upload/progress endpoint."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest


@pytest.fixture
def agent_id():
    """Generate a test agent UUID."""
    return uuid4()


@pytest.fixture
def job_id():
    """Generate a test job UUID."""
    return uuid4()


@pytest.fixture
def file_id():
    """Generate a test file UUID."""
    return uuid4()


@pytest.fixture
def mock_db():
    """Mock database session."""
    return AsyncMock()


@pytest.mark.asyncio
async def test_report_progress_updates_status(
    mock_db,
    agent_id,
    job_id,
    file_id
):
    """Test progress update transitions file to UPLOADING status."""
    # This test will fail until we implement the endpoint
    with pytest.raises(ImportError):
        pass


@pytest.mark.asyncio
async def test_report_progress_illegal_transition(
    mock_db,
    agent_id,
    job_id,
    file_id
):
    """Test that illegal status transitions (SYNCED -> UPLOADING) are rejected."""
    # This test will fail until we implement the endpoint
    with pytest.raises(ImportError):
        pass


@pytest.mark.asyncio
async def test_report_progress_multi_file_job(
    mock_db,
    agent_id,
    job_id
):
    """Test that independent file statuses are tracked correctly in multi-file jobs."""
    # This test will fail until we implement the endpoint
    with pytest.raises(ImportError):
        pass
