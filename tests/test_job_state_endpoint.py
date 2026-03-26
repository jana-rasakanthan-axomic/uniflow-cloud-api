"""Tests for PATCH /jobs/{job_id}/state endpoint."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from app.exceptions.job_exceptions import InvalidTransitionError
from app.main import app
from app.models.job import Job
from app.shared.enums.job_status import JobStatus


class TestPatchJobState:
    """Test PATCH /api/v1/jobs/{job_id}/state endpoint."""

    @pytest.fixture
    def sample_job(self):
        """Create a sample job."""
        job = MagicMock(spec=Job)
        job.id = uuid4()
        job.status = JobStatus.IN_PROGRESS
        job.org_id = uuid4()
        job.collection_id = uuid4()
        job.expires_at = datetime.now(UTC) + timedelta(days=7)
        job.completed_at = None
        job.created_at = datetime.now(UTC)
        job.updated_at = datetime.now(UTC)
        return job

    @pytest.mark.asyncio
    async def test_patch_job_state_success(self, sample_job):
        """Valid transition returns 200 with updated job."""
        job_id = sample_job.id

        # Mock the JobService.transition_state method
        with patch("app.api.routers.web.JobService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.transition_state = AsyncMock(return_value=sample_job)
            mock_service_class.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.patch(
                    f"/api/v1/jobs/{job_id}/state",
                    json={"action": "complete"},
                )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["job_id"] == str(job_id)
            assert data["status"] == JobStatus.IN_PROGRESS
            assert "transitioned_at" in data

    @pytest.mark.asyncio
    async def test_patch_job_state_conflict(self, sample_job):
        """Invalid transition returns 409 with conflict error."""
        job_id = sample_job.id

        # Mock the JobService to raise InvalidTransitionError
        with patch("app.api.routers.web.JobService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.transition_state = AsyncMock(
                side_effect=InvalidTransitionError(JobStatus.COMPLETED, "cancel")
            )
            mock_service_class.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.patch(
                    f"/api/v1/jobs/{job_id}/state",
                    json={"action": "cancel"},
                )

            assert response.status_code == status.HTTP_409_CONFLICT
            data = response.json()
            assert "detail" in data
            assert data["current_state"] == JobStatus.COMPLETED
            assert data["attempted_action"] == "cancel"

    @pytest.mark.asyncio
    async def test_patch_job_not_found(self):
        """Job not found returns 404."""
        job_id = uuid4()

        # Mock the JobService to raise ValueError (job not found)
        with patch("app.api.routers.web.JobService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.transition_state = AsyncMock(
                side_effect=ValueError(f"Job not found: {job_id}")
            )
            mock_service_class.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.patch(
                    f"/api/v1/jobs/{job_id}/state",
                    json={"action": "consent"},
                )

            assert response.status_code == status.HTTP_404_NOT_FOUND
            data = response.json()
            assert "detail" in data

    @pytest.mark.asyncio
    async def test_patch_invalid_action(self):
        """Invalid action in request returns 422 validation error."""
        job_id = uuid4()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.patch(
                f"/api/v1/jobs/{job_id}/state",
                json={"action": "invalid_action"},
            )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_patch_missing_action(self):
        """Missing action field returns 422 validation error."""
        job_id = uuid4()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.patch(
                f"/api/v1/jobs/{job_id}/state",
                json={},
            )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "detail" in data
