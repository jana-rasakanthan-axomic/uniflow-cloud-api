"""Upload service for progress tracking and finalization."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.file_repository import FileRepository
from app.services.oa_client_service import OAClientService


class UploadService:
    """Service for upload progress tracking and file finalization."""

    def __init__(self):
        """Initialize upload service."""
        self.file_repository = FileRepository()
        self.oa_client_service = OAClientService()

    async def finalize_file_upload(
        self,
        db: AsyncSession,
        file_id: UUID,
        streaming_hash: str
    ) -> None:
        """Verify hash and finalize upload with OpenAsset.

        Args:
            db: Database session
            file_id: File UUID
            streaming_hash: SHA-256 hash computed during upload

        Flow:
            - Compare streaming_hash against pre-registered hash
            - On match: mark SYNCED, call OA finalization API
            - On mismatch: mark FAILED, trigger ghost cleanup
        """
        # TODO: Implement hash verification and finalization
        # This will be implemented in Phase 4
        pass
