"""Tests for JobService - Mock repository tests."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.exceptions.job_exceptions import InvalidTransitionError
from app.models.job import Job
from app.services.job_service import JobService
from app.shared.enums.job_status import JobStatus


class TestTransitionState:
    """Test JobService.transition_state method."""

    @pytest.fixture
    def job_service(self):
        """Create JobService instance."""
        return JobService()

    @pytest.fixture
    def mock_job_repo(self):
        """Create mock JobRepository."""
        repo = MagicMock()
        repo.update_state = AsyncMock()
        return repo

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def sample_job(self):
        """Create a sample job in WAITING_FOR_AGENT state."""
        job = MagicMock(spec=Job)
        job.id = uuid4()
        job.status = JobStatus.WAITING_FOR_AGENT
        job.org_id = uuid4()
        job.collection_id = uuid4()
        job.expires_at = datetime.now(UTC) + timedelta(days=7)
        job.completed_at = None
        job.created_at = datetime.now(UTC)
        job.updated_at = datetime.now(UTC)
        return job

    async def test_transition_state_success(
        self, job_service, mock_db, mock_job_repo, sample_job
    ):
        """Valid transition calls repository and returns updated job."""
        # Arrange
        job_id = sample_job.id
        updated_job = MagicMock(spec=Job)
        updated_job.id = job_id
        updated_job.status = JobStatus.IN_PROGRESS

        # Mock repository methods
        mock_job_repo.find_by_id = AsyncMock(return_value=sample_job)
        mock_job_repo.update_state = AsyncMock(return_value=updated_job)

        # Act
        result = await job_service.transition_state(
            mock_db, job_id, "consent", mock_job_repo
        )

        # Assert
        assert result.status == JobStatus.IN_PROGRESS
        mock_job_repo.find_by_id.assert_awaited_once_with(mock_db, job_id)
        mock_job_repo.update_state.assert_awaited_once_with(
            mock_db, job_id, JobStatus.IN_PROGRESS
        )

    async def test_transition_state_invalid(
        self, job_service, mock_db, mock_job_repo, sample_job
    ):
        """Invalid transition raises InvalidTransitionError without DB call."""
        # Arrange
        job_id = sample_job.id
        mock_job_repo.find_by_id = AsyncMock(return_value=sample_job)

        # Act & Assert
        with pytest.raises(InvalidTransitionError) as exc_info:
            await job_service.transition_state(
                mock_db, job_id, "complete_registration", mock_job_repo
            )

        assert exc_info.value.current_state == JobStatus.WAITING_FOR_AGENT
        assert exc_info.value.action == "complete_registration"

        # Repository should have been called to find job, but NOT to update
        mock_job_repo.find_by_id.assert_awaited_once_with(mock_db, job_id)
        assert mock_job_repo.update_state.await_count == 0

    async def test_transition_state_job_not_found(
        self, job_service, mock_db, mock_job_repo
    ):
        """Missing job raises ValueError."""
        # Arrange
        job_id = uuid4()
        mock_job_repo.find_by_id = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(ValueError, match="Job not found"):
            await job_service.transition_state(
                mock_db, job_id, "consent", mock_job_repo
            )

        mock_job_repo.find_by_id.assert_awaited_once_with(mock_db, job_id)
        assert mock_job_repo.update_state.await_count == 0

    async def test_transition_from_terminal_state(
        self, job_service, mock_db, mock_job_repo
    ):
        """Attempting transition from terminal state raises InvalidTransitionError."""
        # Arrange
        completed_job = MagicMock(spec=Job)
        completed_job.id = uuid4()
        completed_job.status = JobStatus.COMPLETED

        mock_job_repo.find_by_id = AsyncMock(return_value=completed_job)

        # Act & Assert
        with pytest.raises(InvalidTransitionError) as exc_info:
            await job_service.transition_state(
                mock_db, completed_job.id, "cancel", mock_job_repo
            )

        assert exc_info.value.current_state == JobStatus.COMPLETED
        assert exc_info.value.action == "cancel"
        assert mock_job_repo.update_state.await_count == 0


class TestCheckTimeouts:
    """Test JobService.check_timeouts method."""

    @pytest.fixture
    def job_service(self):
        """Create JobService instance."""
        return JobService()

    @pytest.fixture
    def mock_job_repo(self):
        """Create mock JobRepository."""
        repo = MagicMock()
        repo.update_state = AsyncMock()
        return repo

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    async def test_check_timeouts_finds_expired_jobs(
        self, job_service, mock_db, mock_job_repo
    ):
        """Finds and transitions expired jobs to TIMEOUT."""
        # Arrange
        expired_job1 = MagicMock(spec=Job)
        expired_job1.id = uuid4()
        expired_job1.status = JobStatus.WAITING_FOR_AGENT
        expired_job1.expires_at = datetime.now(UTC) - timedelta(hours=1)

        expired_job2 = MagicMock(spec=Job)
        expired_job2.id = uuid4()
        expired_job2.status = JobStatus.WAITING_FOR_AGENT
        expired_job2.expires_at = datetime.now(UTC) - timedelta(days=1)

        mock_job_repo.find_expired_jobs = AsyncMock(
            return_value=[expired_job1, expired_job2]
        )
        mock_job_repo.update_state = AsyncMock()

        # Act
        result = await job_service.check_timeouts(mock_db, mock_job_repo)

        # Assert
        assert len(result) == 2
        assert expired_job1.id in result
        assert expired_job2.id in result

        # Should have called update_state for each expired job
        assert mock_job_repo.update_state.await_count == 2
        mock_job_repo.update_state.assert_any_await(
            mock_db, expired_job1.id, JobStatus.TIMEOUT
        )
        mock_job_repo.update_state.assert_any_await(
            mock_db, expired_job2.id, JobStatus.TIMEOUT
        )

    async def test_check_timeouts_no_expired_jobs(
        self, job_service, mock_db, mock_job_repo
    ):
        """Returns empty list when no jobs are expired."""
        # Arrange
        mock_job_repo.find_expired_jobs = AsyncMock(return_value=[])

        # Act
        result = await job_service.check_timeouts(mock_db, mock_job_repo)

        # Assert
        assert result == []
        assert mock_job_repo.update_state.await_count == 0

    async def test_check_timeouts_only_waiting_for_agent_state(
        self, job_service, mock_db, mock_job_repo
    ):
        """Only transitions jobs in WAITING_FOR_AGENT state (via repository query)."""
        # Arrange - This test verifies the service calls repository correctly
        expired_job = MagicMock(spec=Job)
        expired_job.id = uuid4()
        expired_job.status = JobStatus.WAITING_FOR_AGENT
        expired_job.expires_at = datetime.now(UTC) - timedelta(hours=1)

        # Repository returns only WAITING_FOR_AGENT jobs
        mock_job_repo.find_expired_jobs = AsyncMock(return_value=[expired_job])
        mock_job_repo.update_state = AsyncMock()

        # Act
        result = await job_service.check_timeouts(mock_db, mock_job_repo)

        # Assert
        assert len(result) == 1
        mock_job_repo.find_expired_jobs.assert_awaited_once_with(mock_db)
