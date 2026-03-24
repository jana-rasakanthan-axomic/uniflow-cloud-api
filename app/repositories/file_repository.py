"""File repository for job_files database operations."""

from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job_file import JobFile


class FileRepository:
    """Repository for job_files CRUD operations.

    Handles database access for individual file records within jobs,
    including bulk operations and status updates.
    """

    async def bulk_create(
        self,
        db: AsyncSession,
        job_id: UUID,
        asset_ids: list[UUID],
        initial_status: str = "DISCOVERED"
    ) -> list[JobFile]:
        """Create multiple job_file records in bulk.

        Args:
            db: Database session
            job_id: Job UUID
            asset_ids: List of asset UUIDs
            initial_status: Initial status for all files (default: DISCOVERED)

        Returns:
            List of created JobFile instances
        """
        job_files = []
        for asset_id in asset_ids:
            job_file = JobFile(
                id=uuid4(),
                job_id=job_id,
                asset_id=asset_id,
                oa_asset_id=None,
                status=initial_status,
                chunks_completed=0,
                total_chunks=0,
                error_message=None
            )
            db.add(job_file)
            job_files.append(job_file)

        await db.flush()
        return job_files

    async def update_status(
        self,
        db: AsyncSession,
        job_file_id: UUID,
        new_status: str,
        oa_asset_id: str | None = None,
        error_message: str | None = None
    ) -> JobFile:
        """Update job_file status and optional fields.

        Args:
            db: Database session
            job_file_id: JobFile UUID
            new_status: New status value
            oa_asset_id: Optional OpenAsset asset ID
            error_message: Optional error message

        Returns:
            Updated JobFile instance
        """
        update_values = {"status": new_status}

        if oa_asset_id is not None:
            update_values["oa_asset_id"] = oa_asset_id

        if error_message is not None:
            update_values["error_message"] = error_message

        await db.execute(
            update(JobFile)
            .where(JobFile.id == job_file_id)
            .values(**update_values)
        )
        await db.flush()

        # Retrieve and return updated job_file
        result = await db.execute(
            select(JobFile).where(JobFile.id == job_file_id)
        )
        return result.scalar_one()

    async def find_by_job_id(
        self,
        db: AsyncSession,
        job_id: UUID
    ) -> list[JobFile]:
        """Find all job_files for a given job.

        Args:
            db: Database session
            job_id: Job UUID

        Returns:
            List of JobFile instances
        """
        result = await db.execute(
            select(JobFile).where(JobFile.job_id == job_id)
        )
        return list(result.scalars().all())

    async def bulk_update_status(
        self,
        db: AsyncSession,
        job_file_ids: list[UUID],
        new_status: str
    ) -> None:
        """Update status for multiple job_files in bulk.

        Args:
            db: Database session
            job_file_ids: List of JobFile UUIDs
            new_status: New status value
        """
        await db.execute(
            update(JobFile)
            .where(JobFile.id.in_(job_file_ids))
            .values(status=new_status)
        )
        await db.flush()
