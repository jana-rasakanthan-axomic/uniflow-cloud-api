"""SetupCode model."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CHAR, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.organization import Organization


class SetupCode(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """SetupCode model - one-time codes for device activation."""

    __tablename__ = "setup_codes"

    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    code: Mapped[str] = mapped_column(CHAR(8), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationship
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="setup_codes", lazy="selectin"
    )
