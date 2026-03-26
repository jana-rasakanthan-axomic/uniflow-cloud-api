"""Tests for POST /edge/upload/progress endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_agent_id_from_jwt
from app.api.routers.edge import router as edge_router
from app.database import get_db


@pytest.fixture
def agent_id():
    return uuid4()


@pytest.fixture
def job_id():
    return uuid4()


@pytest.fixture
def file_id():
    return uuid4()


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


class TestUploadProgress:
    """Test POST /edge/upload/progress endpoint."""

    @patch("app.api.routers.edge.FileRepository")
    def test_report_progress_updates_status(
        self, mock_repo_cls, client, job_id, file_id
    ):
        """Test progress update transitions file to UPLOADING status."""
        mock_file = MagicMock()
        mock_file.status = "UPLOADING"
        mock_repo = mock_repo_cls.return_value
        mock_repo.update_file_status = AsyncMock(return_value=mock_file)

        response = client.post("/edge/upload/progress", json={
            "job_id": str(job_id),
            "file_id": str(file_id),
            "chunks_completed": 5,
            "total_chunks": 10,
            "status": "UPLOADING",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["ack"] is True
        assert data["file_status"] == "UPLOADING"

    @patch("app.api.routers.edge.FileRepository")
    def test_report_progress_illegal_transition(
        self, mock_repo_cls, client, job_id, file_id
    ):
        """Test that illegal status transitions are rejected with 400."""
        mock_repo = mock_repo_cls.return_value
        mock_repo.update_file_status = AsyncMock(
            side_effect=ValueError("Invalid transition: SYNCED -> UPLOADING")
        )

        response = client.post("/edge/upload/progress", json={
            "job_id": str(job_id),
            "file_id": str(file_id),
            "chunks_completed": 10,
            "total_chunks": 10,
            "status": "UPLOADING",
        })

        assert response.status_code == 400
        assert "Invalid transition" in response.json()["detail"]

    @patch("app.api.routers.edge.FileRepository")
    def test_report_progress_multi_file_job(
        self, mock_repo_cls, client, job_id
    ):
        """Test that independent file statuses are tracked correctly in multi-file jobs."""
        file_id_a = uuid4()
        file_id_b = uuid4()

        mock_file_a = MagicMock()
        mock_file_a.status = "UPLOADING"
        mock_file_b = MagicMock()
        mock_file_b.status = "PAUSED"

        mock_repo = mock_repo_cls.return_value
        mock_repo.update_file_status = AsyncMock(side_effect=[mock_file_a, mock_file_b])

        resp_a = client.post("/edge/upload/progress", json={
            "job_id": str(job_id),
            "file_id": str(file_id_a),
            "chunks_completed": 3,
            "total_chunks": 10,
            "status": "UPLOADING",
        })
        resp_b = client.post("/edge/upload/progress", json={
            "job_id": str(job_id),
            "file_id": str(file_id_b),
            "chunks_completed": 5,
            "total_chunks": 10,
            "status": "PAUSED",
        })

        assert resp_a.status_code == 200
        assert resp_a.json()["file_status"] == "UPLOADING"
        assert resp_b.status_code == 200
        assert resp_b.json()["file_status"] == "PAUSED"
