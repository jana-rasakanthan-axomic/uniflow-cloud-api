"""Signaling service for long-poll and stale agent detection."""

import asyncio
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.command import Command
from app.repositories.command_repository import CommandRepository
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
        self.command_repository = CommandRepository()
        self.active_poll_agent_ids: set[UUID] = set()
        self._poll_events: dict[UUID, asyncio.Event] = {}
        self._events_lock = asyncio.Lock()

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

    async def hold_poll(
        self,
        db: AsyncSession,
        agent_id: UUID,
        timeout: float = 55.0
    ) -> Command | None:
        """Hold long-poll connection for agent, returning command if available.

        Flow:
        1. Check for pending command first (immediate return if found)
        2. If not found, create Event and wait with timeout
        3. On wake (event set) or timeout, check for pending command again
        4. Clean up event in finally block

        Args:
            db: Database session
            agent_id: Agent UUID
            timeout: Timeout in seconds (default 55.0)

        Returns:
            Command if available, None on timeout
        """
        # Check for pending command first
        command = await self.command_repository.pop_pending(db, agent_id)
        if command is not None:
            return command

        # Create event for this agent
        event = asyncio.Event()
        async with self._events_lock:
            self._poll_events[agent_id] = event
            self.active_poll_agent_ids.add(agent_id)

        try:
            # Wait for event to be set or timeout
            try:
                await asyncio.wait_for(event.wait(), timeout=timeout)
            except TimeoutError:
                # Timeout expired, check for command one more time
                pass

            # Check for pending command (may have been added while we were waiting)
            command = await self.command_repository.pop_pending(db, agent_id)
            return command
        finally:
            # Clean up event
            async with self._events_lock:
                self._poll_events.pop(agent_id, None)
                self.active_poll_agent_ids.discard(agent_id)

    async def dispatch_command(self, db: AsyncSession, agent_id: UUID) -> None:
        """Set event to wake held connection for agent.

        Args:
            db: Database session (for consistency with interface, not used)
            agent_id: Agent UUID to wake
        """
        async with self._events_lock:
            event = self._poll_events.get(agent_id)
            if event is not None:
                event.set()

    def get_active_poll_agents(self) -> set[UUID]:
        """Return currently polling agents.

        Returns:
            Set of agent UUIDs with active polls
        """
        return set(self._poll_events.keys())

    async def close_all_connections(self) -> None:
        """Wake all held connections on shutdown."""
        async with self._events_lock:
            for event in self._poll_events.values():
                event.set()
            # Events will be cleaned up by hold_poll finally blocks
