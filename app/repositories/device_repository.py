"""Device repository for database operations."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device
from app.shared.enums import DeviceStatus


class DeviceRepository:
    """Repository for device CRUD operations.

    Handles database access for devices including status updates,
    stale device detection, and metadata management.
    """

    async def find_stale(
        self,
        db: AsyncSession,
        threshold_seconds: int,
        exclude_agent_ids: list[UUID] | None = None
    ) -> list[Device]:
        """Find ONLINE devices with last_seen_at older than threshold.

        Args:
            db: Database session
            threshold_seconds: Threshold in seconds (e.g., 110 for 110 seconds)
            exclude_agent_ids: List of agent_ids to exclude (active long-poll)

        Returns:
            List of stale Device instances
        """
        if exclude_agent_ids is None:
            exclude_agent_ids = []

        # Calculate cutoff time
        cutoff_time = datetime.now(UTC) - timedelta(seconds=threshold_seconds)

        # Build query
        query = select(Device).where(
            Device.status == DeviceStatus.ONLINE.value,
            Device.last_seen_at < cutoff_time
        )

        # Exclude active agents if provided
        if exclude_agent_ids:
            query = query.where(Device.agent_id.notin_(exclude_agent_ids))

        # Execute query
        result = await db.execute(query)
        return list(result.scalars().all())

    async def update_status(
        self,
        db: AsyncSession,
        agent_id: UUID,
        status: DeviceStatus,
        last_seen: datetime | None = None,
        metadata: dict | None = None
    ) -> Device | None:
        """Update device status and last_seen_at timestamp with optimistic locking.

        Args:
            db: Database session
            agent_id: Device agent UUID
            status: New device status
            last_seen: Explicit last_seen timestamp (defaults to now)
            metadata: Optional metadata dictionary to store

        Returns:
            Updated Device instance or None if not found

        Note:
            Uses optimistic locking to prevent updating with stale timestamps.
            Only updates if the new last_seen is >= current last_seen_at.
        """
        # Use current time if not provided
        if last_seen is None:
            last_seen = datetime.now(UTC)

        # Build update values
        update_values: dict[str, Any] = {
            "status": status.value,
            "last_seen_at": last_seen
        }

        # Add metadata if provided
        if metadata is not None:
            update_values["device_metadata"] = metadata

        # Execute update with optimistic locking
        # Only update if new timestamp is >= current timestamp
        await db.execute(
            update(Device)
            .where(Device.agent_id == agent_id)
            .where(Device.last_seen_at <= last_seen)
            .values(**update_values)
        )
        await db.flush()

        # Fetch and return updated device
        result = await db.execute(
            select(Device).where(Device.agent_id == agent_id)
        )
        return result.scalar_one_or_none()
