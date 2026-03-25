"""Command service for queuing and delivery."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.command import Command
from app.repositories.command_repository import CommandRepository
from app.services.signaling_service import SignalingService


class CommandService:
    """Service for command business logic."""

    VALID_COMMAND_TYPES = {"upload_request", "pause", "resume", "refresh_scan"}

    def __init__(self):
        """Initialize command service."""
        self.command_repository = CommandRepository()
        self.signaling_service = SignalingService()

    async def create_command(
        self,
        db: AsyncSession,
        agent_id: UUID,
        command_type: str,
        payload: dict
    ) -> Command:
        """Create a new command and dispatch to agent.

        Args:
            db: Database session
            agent_id: Target agent UUID
            command_type: Command type (must be in VALID_COMMAND_TYPES)
            payload: Command payload dict

        Returns:
            Created Command instance

        Raises:
            ValueError: If command_type is invalid
        """
        # Validate command type
        if command_type not in self.VALID_COMMAND_TYPES:
            raise ValueError(
                f"Invalid command type: {command_type}. "
                f"Must be one of: {', '.join(self.VALID_COMMAND_TYPES)}"
            )

        # Create command record
        command = Command(
            agent_id=agent_id,
            type=command_type,
            payload_json=payload,
            status="PENDING",
            created_at=datetime.now(UTC)
        )

        db.add(command)
        await db.flush()
        await db.refresh(command)

        # Dispatch to wake held connection (if any)
        await self.signaling_service.dispatch_command(db, agent_id)

        return command

    async def expire_stale_commands(
        self,
        db: AsyncSession,
        threshold_hours: int = 24
    ) -> int:
        """Mark commands older than threshold as EXPIRED.

        Args:
            db: Database session
            threshold_hours: Age threshold in hours (default: 24)

        Returns:
            Count of commands expired
        """
        return await self.command_repository.expire_old_commands(
            db=db,
            threshold_hours=threshold_hours
        )
