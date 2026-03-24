"""JobFile model."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.asset import Asset
    from app.models.job import Job


class JobFile(Base, UUIDPrimaryKeyMixin):
    """JobFile model - tracks individual file upload status within a job."""

    __tablename__ = "job_files"

    job_id: Mapped[UUID] = mapped_column(ForeignKey("jobs.id"), nullable=False)
    asset_id: Mapped[UUID] = mapped_column(ForeignKey("assets.id"), nullable=False)
    oa_asset_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(nullable=False)
    chunks_completed: Mapped[int] = mapped_column(nullable=False)
    total_chunks: Mapped[int] = mapped_column(nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="files", lazy="selectin")
    asset: Mapped["Asset"] = relationship("Asset", lazy="selectin")

    __table_args__ = (
        CheckConstraint(
            "status IN ('DISCOVERED', 'PRE_REGISTERED', 'UPLOADING', 'PAUSED', "
            "'PAUSED_USER', 'SYNCED', 'FAILED', 'CANCELLED')",
            name="job_file_status_check",
        ),
    )
