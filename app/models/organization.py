"""Organization model."""

from typing import TYPE_CHECKING

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.collection import Collection
    from app.models.device import Device
    from app.models.job import Job
    from app.models.setup_code import SetupCode
    from app.models.user import User


class Organization(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Organization model - top-level entity for multi-tenancy."""

    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    job_timeout_days: Mapped[int] = mapped_column(default=7, nullable=False)
    oa_api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    users: Mapped[list["User"]] = relationship(
        "User", back_populates="organization", lazy="selectin"
    )
    devices: Mapped[list["Device"]] = relationship(
        "Device", back_populates="organization", lazy="selectin"
    )
    setup_codes: Mapped[list["SetupCode"]] = relationship(
        "SetupCode", back_populates="organization", lazy="selectin"
    )
    collections: Mapped[list["Collection"]] = relationship(
        "Collection", back_populates="organization", lazy="selectin"
    )
    jobs: Mapped[list["Job"]] = relationship(
        "Job", back_populates="organization", lazy="selectin"
    )
