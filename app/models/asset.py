"""Asset model."""

from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import BIGINT, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.folder import Folder


class Asset(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Asset model - represents a file on disk."""

    __tablename__ = "assets"

    folder_id: Mapped[UUID] = mapped_column(ForeignKey("folders.id"), nullable=False)
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[int] = mapped_column(BIGINT, nullable=False)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str] = mapped_column(Text, nullable=False)
    exif_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationship
    folder: Mapped["Folder"] = relationship("Folder", back_populates="assets", lazy="selectin")
