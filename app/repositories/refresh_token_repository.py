"""RefreshToken repository for database operations."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import lazyload

from app.models.refresh_token import RefreshToken


class RefreshTokenRepository:
    """Repository for refresh token CRUD operations.

    Handles database access for refresh tokens including creation,
    lookup by hash, single token revocation, and chain revocation.
    """

    async def create(self, db: AsyncSession, token: RefreshToken) -> RefreshToken:
        """Create a new refresh token record.

        Args:
            db: Database session
            token: RefreshToken instance to create

        Returns:
            Created RefreshToken instance
        """
        db.add(token)
        await db.flush()  # Flush to get the ID without committing
        return token

    async def find_by_token_hash(
        self, db: AsyncSession, token_hash: str
    ) -> RefreshToken | None:
        """Find a refresh token by its hash.

        Args:
            db: Database session
            token_hash: SHA-256 hash of the token

        Returns:
            RefreshToken instance if found, None otherwise
        """
        result = await db.execute(
            select(RefreshToken)
            .where(RefreshToken.token_hash == token_hash)
            .options(lazyload("*"))
        )
        return result.scalar_one_or_none()

    async def revoke(self, db: AsyncSession, token_id: UUID) -> None:
        """Mark a single token as revoked.

        Args:
            db: Database session
            token_id: Token UUID to revoke
        """
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.id == token_id)
            .values(revoked_at=datetime.now(UTC))
        )
        await db.flush()

    async def revoke_chain(self, db: AsyncSession, chain_id: UUID) -> int:
        """Revoke all tokens with the given chain_id.

        Args:
            db: Database session
            chain_id: Token chain UUID

        Returns:
            Number of tokens revoked
        """
        result = await db.execute(
            update(RefreshToken)
            .where(RefreshToken.chain_id == chain_id)
            .values(revoked_at=datetime.now(UTC))
        )
        await db.flush()
        return result.rowcount  # type: ignore
