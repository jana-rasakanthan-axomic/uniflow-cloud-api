"""Job model."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.collection import Collection
    from app.models.job_file import JobFile
    from app.models.organization import Organization


class Job(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Job model - represents a submission job to OpenAsset."""

    __tablename__ = "jobs"

    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    collection_id: Mapped[UUID] = mapped_column(
        ForeignKey("collections.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="jobs", lazy="selectin"
    )
    collection: Mapped["Collection"] = relationship(
        "Collection", back_populates="jobs", lazy="selectin"
    )
    files: Mapped[list["JobFile"]] = relationship(
        "JobFile", back_populates="job", lazy="selectin"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('PRE_REGISTERING', 'WAITING_FOR_AGENT', 'IN_PROGRESS', "
            "'PAUSED_USER', 'COMPLETED', 'PARTIALLY_FAILED', 'FAILED', "
            "'CANCELLED', 'DENIED', 'TIMEOUT')",
            name="job_status_check",
        ),
    )
