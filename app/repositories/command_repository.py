"""Command repository for atomic command operations."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.command import Command


class CommandRepository:
    """Repository for command data operations."""

    async def pop_pending(self, db: AsyncSession, agent_id: UUID) -> Command | None:
        """Atomically fetch oldest PENDING command and mark as DELIVERED.

        Args:
            db: Database session
            agent_id: Agent UUID to fetch commands for

        Returns:
            Command object if found, None otherwise
        """
        # Find oldest PENDING command for this agent
        stmt = (
            select(Command)
            .where(Command.agent_id == agent_id)
            .where(Command.status == "PENDING")
            .order_by(Command.created_at.asc())
            .limit(1)
        )

        result = await db.execute(stmt)
        command = result.scalar_one_or_none()

        if command is None:
            return None

        # Mark as DELIVERED
        command.status = "DELIVERED"
        command.delivered_at = datetime.now(UTC)

        # Commit the change
        await db.commit()
        await db.refresh(command)

        return command

    async def expire_old_commands(
        self,
        db: AsyncSession,
        threshold_hours: int = 24
    ) -> int:
        """Mark commands older than threshold as EXPIRED.

        Args:
            db: Database session
            threshold_hours: Age threshold in hours

        Returns:
            Count of commands marked as EXPIRED
        """
        # Calculate threshold timestamp
        threshold = datetime.now(UTC) - timedelta(hours=threshold_hours)

        # Update old PENDING commands to EXPIRED
        stmt = (
            update(Command)
            .where(Command.created_at < threshold)
            .where(Command.status == "PENDING")
            .values(status="EXPIRED")
        )

        result: CursorResult = await db.execute(stmt)  # type: ignore[assignment]
        await db.flush()

        return result.rowcount if result.rowcount else 0
