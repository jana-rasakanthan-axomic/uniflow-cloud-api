"""Job Service - Business logic for job state management.

Orchestrates state transitions and timeout handling using the state machine
and repository layer.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from app.repositories.job_repository import JobRepository
from app.services.state_machine import JobStateMachine
from app.shared.enums.job_status import JobStatus


class JobService:
    """Service layer for job state management.

    Validates state transitions using JobStateMachine and persists
    changes through JobRepository.
    """

    async def transition_state(
        self,
        db: AsyncSession,
        job_id: UUID,
        action: str,
        job_repo: JobRepository | None = None,
    ) -> Job:
        """Transition a job to a new state based on an action.

        Args:
            db: Database session
            job_id: Job UUID
            action: Action to perform (e.g., "consent", "cancel", "complete")
            job_repo: JobRepository instance (injected for testing)

        Returns:
            Updated Job instance

        Raises:
            ValueError: If job not found
            InvalidTransitionError: If transition is not allowed by state machine
        """
        # Use injected repository or create new instance
        if job_repo is None:
            job_repo = JobRepository()

        # Fetch current job state
        job = await job_repo.find_by_id(db, job_id)
        if job is None:
            raise ValueError(f"Job not found: {job_id}")

        # Validate transition with state machine (raises InvalidTransitionError if invalid)
        next_state = JobStateMachine.get_next_state(job.status, action)

        # Persist state change
        updated_job = await job_repo.update_state(db, job_id, next_state)

        return updated_job

    async def check_timeouts(
        self,
        db: AsyncSession,
        job_repo: JobRepository | None = None,
    ) -> list[UUID]:
        """Find and transition expired jobs to TIMEOUT state.

        Args:
            db: Database session
            job_repo: JobRepository instance (injected for testing)

        Returns:
            List of job IDs that were transitioned to TIMEOUT
        """
        # Use injected repository or create new instance
        if job_repo is None:
            job_repo = JobRepository()

        # Find expired jobs
        expired_jobs = await job_repo.find_expired_jobs(db)

        transitioned_ids = []
        for job in expired_jobs:
            # Transition to TIMEOUT using state machine
            try:
                await job_repo.update_state(db, job.id, JobStatus.TIMEOUT)
                transitioned_ids.append(job.id)
            except Exception:
                # Log error but continue processing other jobs
                # In production, would use proper logging
                continue

        return transitioned_ids
