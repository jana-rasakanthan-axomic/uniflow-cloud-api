"""AuditLog model.

BR-25: Application role has INSERT-only permission on this table.
No UPDATE or DELETE operations are permitted to ensure audit immutability.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.organization import Organization


class AuditLog(Base):
    """AuditLog model - immutable audit trail for compliance (BR-25)."""

    __tablename__ = "audit_log"

    # BIGSERIAL auto-increment primary key (not UUID)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    org_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    actor_id: Mapped[UUID | None] = mapped_column(nullable=True)
    source_ip: Mapped[str] = mapped_column(INET, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    # Relationships
    organization: Mapped["Organization | None"] = relationship(
        "Organization", lazy="selectin"
    )
