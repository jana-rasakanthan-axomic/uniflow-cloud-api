"""Folder model."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.asset import Asset
    from app.models.device import Device


class Folder(Base, UUIDPrimaryKeyMixin):
    """Folder model - represents a watched directory on a device."""

    __tablename__ = "folders"

    device_id: Mapped[UUID] = mapped_column(ForeignKey("devices.id"), nullable=False)
    path_hash: Mapped[str] = mapped_column(Text, nullable=False)
    relative_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_count: Mapped[int] = mapped_column(nullable=False)
    last_scan_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    device: Mapped["Device"] = relationship("Device", back_populates="folders", lazy="selectin")
    assets: Mapped[list["Asset"]] = relationship(
        "Asset", back_populates="folder", lazy="selectin"
    )
