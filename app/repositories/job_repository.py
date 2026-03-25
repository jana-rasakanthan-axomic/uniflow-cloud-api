"""Job repository for database operations."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import lazyload

from app.models.job import Job
from app.shared.enums.job_status import JobStatus


class JobRepository:
    """Repository for job CRUD operations.

    Handles database access for jobs including creation, state updates,
    and retrieval operations.
    """

    async def create(
        self,
        db: AsyncSession,
        job_id: UUID,
        org_id: UUID,
        collection_id: UUID,
        status: str,
        expires_at: datetime
    ) -> Job:
        """Create a new job record.

        Args:
            db: Database session
            job_id: Job UUID
            org_id: Organization UUID
            collection_id: Collection UUID
            status: Initial job status (typically PRE_REGISTERING)
            expires_at: Job expiration timestamp

        Returns:
            Created Job instance
        """
        job = Job(
            id=job_id,
            org_id=org_id,
            collection_id=collection_id,
            status=status,
            expires_at=expires_at,
            completed_at=None
        )

        db.add(job)
        await db.flush()

        # Re-fetch with lazyload to avoid eager relationship loading
        result = await db.execute(
            select(Job)
            .where(Job.id == job_id)
            .options(lazyload("*"))
        )
        return result.scalar_one()

    async def update_state(
        self,
        db: AsyncSession,
        job_id: UUID,
        new_status: str
    ) -> Job:
        """Update job status.

        Args:
            db: Database session
            job_id: Job UUID
            new_status: New status value

        Returns:
            Updated Job instance
        """
        await db.execute(
            update(Job)
            .where(Job.id == job_id)
            .values(status=new_status)
        )
        await db.flush()

        # Retrieve and return updated job
        result = await db.execute(
            select(Job)
            .where(Job.id == job_id)
            .options(lazyload("*"))
        )
        return result.scalar_one()

    async def find_by_id(
        self,
        db: AsyncSession,
        job_id: UUID
    ) -> Job | None:
        """Find a job by its ID.

        Args:
            db: Database session
            job_id: Job UUID

        Returns:
            Job instance if found, None otherwise
        """
        result = await db.execute(
            select(Job)
            .where(Job.id == job_id)
            .options(lazyload("*"))
        )
        return result.scalar_one_or_none()

    async def find_expired_jobs(self, db: AsyncSession) -> list[Job]:
        """Find jobs that have expired and are in WAITING_FOR_AGENT state.

        Args:
            db: Database session

        Returns:
            List of expired Job instances
        """
        now = datetime.now(UTC)
        result = await db.execute(
            select(Job)
            .where(
                and_(
                    Job.status == JobStatus.WAITING_FOR_AGENT,
                    Job.expires_at < now
                )
            )
            .options(lazyload("*"))
        )
        return list(result.scalars().all())
