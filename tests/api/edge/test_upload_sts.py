"""Tests for POST /edge/upload/sts endpoint."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_agent_id_from_jwt
from app.api.routers.edge import router as edge_router
from app.database import get_db
from app.schemas.upload import STSCredentials, UploadTarget


@pytest.fixture
def agent_id():
    return uuid4()


@pytest.fixture
def job_id():
    return uuid4()


@pytest.fixture
def file_ids():
    return [uuid4(), uuid4(), uuid4()]


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def app(agent_id):
    """Create FastAPI app with overridden dependencies."""
    test_app = FastAPI()
    test_app.include_router(edge_router, prefix="/edge")

    async def override_agent_id():
        return agent_id

    async def override_db():
        return AsyncMock()

    test_app.dependency_overrides[get_agent_id_from_jwt] = override_agent_id
    test_app.dependency_overrides[get_db] = override_db
    return test_app


@pytest.fixture
def client(app):
    return TestClient(app)


class TestUploadSTS:
    """Test POST /edge/upload/sts endpoint."""

    @patch("app.api.routers.edge.STSService")
    @patch("app.api.routers.edge.FileRepository")
    def test_issue_sts_credentials_success(
        self, mock_repo_cls, mock_sts_cls, client, job_id, file_ids
    ):
        """Test successful STS credential issuance."""
        mock_repo = mock_repo_cls.return_value
        mock_repo.verify_agent_ownership = AsyncMock(return_value=True)

        expiry = datetime.now(UTC) + timedelta(hours=12)
        mock_sts = mock_sts_cls.return_value
        mock_sts.issue_sts_credentials = AsyncMock(return_value={
            "credentials": STSCredentials(
                access_key="ASIAXXX",
                secret_key="secret123",
                session_token="token123",
                expiry=expiry,
            ),
            "upload_targets": [
                UploadTarget(
                    file_id=file_ids[0],
                    bucket="dam-bucket",
                    key=f"uploads/org/job/{file_ids[0]}.jpg",
                    oa_asset_id="oa_123",
                )
            ],
        })

        response = client.post("/edge/upload/sts", json={
            "job_id": str(job_id),
            "file_ids": [str(fid) for fid in file_ids],
        })

        assert response.status_code == 200
        data = response.json()
        assert data["credentials"]["access_key"] == "ASIAXXX"
        assert len(data["upload_targets"]) == 1

    @patch("app.api.routers.edge.FileRepository")
    def test_issue_sts_credentials_unauthorized_agent(
        self, mock_repo_cls, client, job_id, file_ids
    ):
        """Test STS credential issuance fails when agent doesn't own files."""
        mock_repo = mock_repo_cls.return_value
        mock_repo.verify_agent_ownership = AsyncMock(return_value=False)

        response = client.post("/edge/upload/sts", json={
            "job_id": str(job_id),
            "file_ids": [str(fid) for fid in file_ids],
        })

        assert response.status_code == 403
        assert "does not own" in response.json()["detail"]

class TestVerifyAgentOwnership:
    """Test FileRepository.verify_agent_ownership."""

    @pytest.mark.asyncio
    async def test_verify_agent_ownership_true(self, mock_db, agent_id, file_ids):
        """Test returns True when agent owns all files."""
        from app.repositories.file_repository import FileRepository

        repo = FileRepository()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = len(file_ids)
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await repo.verify_agent_ownership(mock_db, agent_id, file_ids)
        assert result is True

    @pytest.mark.asyncio
    async def test_verify_agent_ownership_false(self, mock_db, agent_id, file_ids):
        """Test returns False when agent doesn't own all files."""
        from app.repositories.file_repository import FileRepository

        repo = FileRepository()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = len(file_ids) - 1
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await repo.verify_agent_ownership(mock_db, agent_id, file_ids)
        assert result is False
