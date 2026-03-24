"""CollectionAsset association table model."""

from uuid import UUID

from sqlalchemy import ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CollectionAsset(Base):
    """CollectionAsset - many-to-many association between collections and assets."""

    __tablename__ = "collection_assets"

    collection_id: Mapped[UUID] = mapped_column(
        ForeignKey("collections.id"), nullable=False
    )
    asset_id: Mapped[UUID] = mapped_column(ForeignKey("assets.id"), nullable=False)

    __table_args__ = (PrimaryKeyConstraint("collection_id", "asset_id"),)
