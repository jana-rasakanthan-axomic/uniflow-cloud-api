"""Collection model."""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.job import Job
    from app.models.organization import Organization


class Collection(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Collection model - groups assets for submission to OpenAsset."""

    __tablename__ = "collections"

    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    project_code: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="collections", lazy="selectin"
    )
    jobs: Mapped[list["Job"]] = relationship(
        "Job", back_populates="collection", lazy="selectin"
    )
