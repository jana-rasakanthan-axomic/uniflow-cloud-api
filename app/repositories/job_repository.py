"""Job repository for database operations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import lazyload

from app.models.job import Job


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
        # Expire to prevent eager loading of relationships in tests
        db.expire(job)
        return job

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
