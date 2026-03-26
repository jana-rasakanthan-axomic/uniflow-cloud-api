"""Device model."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.folder import Folder
    from app.models.organization import Organization
    from app.models.user import User


class Device(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Device model - edge agent installation."""

    __tablename__ = "devices"

    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    agent_id: Mapped[UUID] = mapped_column(unique=True, nullable=False)
    machine_name: Mapped[str] = mapped_column(Text, nullable=False)
    os: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    device_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="devices", lazy="selectin"
    )
    user: Mapped["User"] = relationship("User", back_populates="devices", lazy="selectin")
    folders: Mapped[list["Folder"]] = relationship(
        "Folder", back_populates="device", lazy="selectin"
    )
