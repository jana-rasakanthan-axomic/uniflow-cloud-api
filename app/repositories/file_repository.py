"""File repository for job_files database operations."""

from typing import Any
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

    async def verify_agent_ownership(
        self,
        db: AsyncSession,
        agent_id: UUID,
        file_ids: list[UUID]
    ) -> bool:
        """Verify that the requesting agent owns all specified files.

        Args:
            db: Database session
            agent_id: Agent UUID requesting access
            file_ids: List of file UUIDs to verify

        Returns:
            True if agent owns all files, False otherwise
        """
        from sqlalchemy import func

        from app.models.asset import Asset
        from app.models.device import Device
        from app.models.folder import Folder

        # Count how many of the requested files belong to this agent
        # Chain: JobFile -> Asset -> Folder -> Device (which has agent_id)
        stmt = (
            select(func.count(JobFile.id))
            .join(Asset, JobFile.asset_id == Asset.id)
            .join(Folder, Asset.folder_id == Folder.id)
            .join(Device, Folder.device_id == Device.id)
            .where(JobFile.id.in_(file_ids))
            .where(Device.agent_id == agent_id)
        )

        result = await db.execute(stmt)
        count = result.scalar_one_or_none()

        # Agent owns all files if count matches number of requested files
        return count == len(file_ids)

    async def update_file_status(
        self,
        db: AsyncSession,
        file_id: UUID,
        status: str,
        chunks_completed: int | None = None,
        total_chunks: int | None = None,
        streaming_hash: str | None = None,
        error_message: str | None = None
    ) -> JobFile:
        """Update file upload status and progress.

        Args:
            db: Database session
            file_id: File UUID
            status: New status value
            chunks_completed: Optional number of chunks completed
            total_chunks: Optional total number of chunks
            streaming_hash: Optional SHA-256 hash computed during upload
            error_message: Optional error message

        Returns:
            Updated JobFile instance

        Raises:
            ValueError: If status transition is invalid
        """
        # Build update values
        update_values: dict[str, Any] = {"status": status}

        if chunks_completed is not None:
            update_values["chunks_completed"] = chunks_completed

        if total_chunks is not None:
            update_values["total_chunks"] = total_chunks

        if streaming_hash is not None:
            update_values["streaming_hash"] = streaming_hash

        if error_message is not None:
            update_values["error_message"] = error_message

        # Execute update
        await db.execute(
            update(JobFile)
            .where(JobFile.id == file_id)
            .values(**update_values)
        )
        await db.flush()

        # Retrieve and return updated file
        result = await db.execute(
            select(JobFile).where(JobFile.id == file_id)
        )
        return result.scalar_one()
