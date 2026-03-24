"""Audit service for immutable event logging.

BR-25: Application role has INSERT-only permission on audit_log table.
No UPDATE or DELETE operations are permitted to ensure audit immutability.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


class AuditService:
    """Service for logging immutable audit events.

    This service only supports INSERT operations on the audit log.
    No update or delete methods are provided to enforce BR-25 compliance.
    """

    async def log_event(
        self,
        db: AsyncSession,
        org_id: UUID | None,
        event_type: str,
        actor_id: UUID | None,
        source_ip: str,
        metadata: dict[str, Any]
    ) -> None:
        """Log an immutable audit event.

        Args:
            db: Database session
            org_id: Organization UUID (nullable for pre-auth events)
            event_type: Event type identifier (e.g., "DEVICE_LINKED")
            actor_id: Actor UUID (nullable for anonymous events)
            source_ip: Source IP address (IPv4 or IPv6)
            metadata: Event metadata as JSON dictionary

        Note:
            This method does NOT commit the transaction. The caller is responsible
            for committing or rolling back based on the overall operation success.
        """
        event = AuditLog(
            org_id=org_id,
            event_type=event_type,
            actor_id=actor_id,
            source_ip=source_ip,
            metadata_json=metadata,
            created_at=datetime.now(UTC)
        )

        db.add(event)
        # Note: No commit here - caller manages transaction
