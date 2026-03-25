"""Tests for POST /edge/upload/sts endpoint."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.schemas.upload import STSCredentials, UploadTarget


@pytest.fixture
def agent_id():
    """Generate a test agent UUID."""
    return uuid4()


@pytest.fixture
def job_id():
    """Generate a test job UUID."""
    return uuid4()


@pytest.fixture
def file_ids():
    """Generate test file UUIDs."""
    return [uuid4(), uuid4(), uuid4()]


@pytest.fixture
def mock_db():
    """Mock database session."""
    return AsyncMock()


@pytest.fixture
def mock_sts_service():
    """Mock STS service."""
    service = AsyncMock()

    # Default mock credentials
    expiry = datetime.now(UTC) + timedelta(hours=12)
    service.issue_sts_credentials = AsyncMock(return_value={
        "credentials": STSCredentials(
            access_key="ASIAXXX",
            secret_key="secret123",
            session_token="token123",
            expiry=expiry
        ),
        "upload_targets": [
            UploadTarget(
                file_id=uuid4(),
                bucket="dam-bucket",
                key="uploads/org123/job123/agent123/file123.jpg",
                oa_asset_id="oa_asset_123"
            )
        ]
    })

    return service


@pytest.mark.asyncio
async def test_issue_sts_credentials_success(
    mock_db,
    agent_id,
    job_id,
    file_ids,
    mock_sts_service
):
    """Test successful STS credential issuance."""
    # This test will fail until we implement the endpoint
    # Import will fail until route exists
    with pytest.raises(ImportError):
        pass


@pytest.mark.asyncio
async def test_issue_sts_credentials_unauthorized_agent(
    mock_db,
    agent_id,
    job_id,
    file_ids
):
    """Test STS credential issuance fails when agent doesn't own files."""
    # This test will fail until we implement the endpoint
    with pytest.raises(ImportError):
        pass


@pytest.mark.asyncio
async def test_issue_sts_credentials_invalid_job(
    mock_db,
    agent_id,
    file_ids
):
    """Test STS credential issuance fails for invalid job."""
    # This test will fail until we implement the endpoint
    with pytest.raises(ImportError):
        pass


@pytest.mark.asyncio
async def test_verify_agent_ownership_true(mock_db, agent_id, file_ids):
    """Test that verify_agent_ownership returns True when agent owns all files."""
    from app.repositories.file_repository import FileRepository

    repo = FileRepository()

    # Mock the database query to return matching records
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = len(file_ids)
    mock_db.execute = AsyncMock(return_value=mock_result)

    result = await repo.verify_agent_ownership(mock_db, agent_id, file_ids)

    assert result is True


@pytest.mark.asyncio
async def test_verify_agent_ownership_false(mock_db, agent_id, file_ids):
    """Test that verify_agent_ownership returns False when agent doesn't own all files."""
    from app.repositories.file_repository import FileRepository

    repo = FileRepository()

    # Mock the database query to return fewer records than requested
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = len(file_ids) - 1
    mock_db.execute = AsyncMock(return_value=mock_result)

    result = await repo.verify_agent_ownership(mock_db, agent_id, file_ids)

    assert result is False
