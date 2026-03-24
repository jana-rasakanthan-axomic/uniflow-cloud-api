"""Signaling service for long-poll and stale agent detection."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.device_repository import DeviceRepository
from app.shared.enums import DeviceStatus


class SignalingService:
    """Service for long-poll signaling and stale agent detection.

    Manages active long-poll connections and periodically checks for
    stale agents (>110s since last poll) to mark them OFFLINE.
    """

    def __init__(self):
        """Initialize signaling service with empty active poll tracking."""
        self.device_repository = DeviceRepository()
        self.active_poll_agent_ids: set[UUID] = set()

    async def check_stale_agents(self, db: AsyncSession) -> int:
        """Find and mark stale agents OFFLINE.

        Finds ONLINE devices with last_seen_at older than 110 seconds
        (accounting for 2 missed poll cycles) and marks them OFFLINE,
        excluding agents with active long-poll connections.

        Args:
            db: Database session

        Returns:
            Count of agents marked stale
        """
        # Find stale devices (110 second threshold = 2 missed poll cycles)
        # Exclude agents with active long-poll connections
        stale_devices = await self.device_repository.find_stale(
            db=db,
            threshold_seconds=110,
            exclude_agent_ids=self.active_poll_agent_ids
        )

        # Mark each stale device OFFLINE, preserving original last_seen_at
        count = 0
        for device in stale_devices:
            await self.device_repository.update_status(
                db=db,
                agent_id=device.agent_id,
                status=DeviceStatus.OFFLINE,
                last_seen=device.last_seen_at  # Preserve original timestamp
            )
            count += 1

        return count
