"""Tests for RefreshTokenRepository."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models.device import Device
from app.models.organization import Organization
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository


@pytest.fixture
async def engine():
    """Create in-memory SQLite engine for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    async with engine.begin() as conn:
        # Create only the tables we need for these tests
        await conn.run_sync(Organization.__table__.create)
        await conn.run_sync(User.__table__.create)
        await conn.run_sync(Device.__table__.create)
        await conn.run_sync(RefreshToken.__table__.create)

    yield engine

    await engine.dispose()


@pytest.fixture
async def db_session(engine):
    """Create async database session for testing."""
    async_session_factory = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_factory() as session:
        yield session


@pytest.fixture
async def test_org(db_session):
    """Create test organization."""
    org = Organization(
        id=uuid4(),
        name="Test Org",
        slug="test-org",
        created_at=datetime.now(UTC)
    )
    db_session.add(org)
    await db_session.flush()
    return org


@pytest.fixture
async def test_user(db_session, test_org):
    """Create test user."""
    user = User(
        id=uuid4(),
        org_id=test_org.id,
        email="test@example.com",
        role="CURATOR",
        created_at=datetime.now(UTC)
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def test_device(db_session, test_org, test_user):
    """Create test device."""
    device = Device(
        id=uuid4(),
        org_id=test_org.id,
        user_id=test_user.id,
        agent_id=uuid4(),
        machine_name="Test Machine",
        os="Test OS",
        status="ONLINE",
        last_seen_at=datetime.now(UTC),
        created_at=datetime.now(UTC)
    )
    db_session.add(device)
    await db_session.flush()
    return device


@pytest.fixture
def repository():
    """Create repository instance."""
    return RefreshTokenRepository()


class TestRefreshTokenRepository:
    """Test RefreshTokenRepository CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_refresh_token(
        self, db_session, repository, test_user, test_device
    ):
        """Test creating a refresh token record."""
        chain_id = uuid4()
        token_hash = "abc123hash"
        expires_at = datetime.now(UTC) + timedelta(days=90)

        token = RefreshToken(
            id=uuid4(),
            user_id=test_user.id,
            device_id=test_device.id,
            token_hash=token_hash,
            chain_id=chain_id,
            sequence_num=1,
            revoked_at=None,
            expires_at=expires_at,
            created_at=datetime.now(UTC)
        )

        result = await repository.create(db_session, token)
        await db_session.commit()

        assert result.id == token.id
        assert result.token_hash == token_hash
        assert result.chain_id == chain_id
        assert result.sequence_num == 1
        assert result.revoked_at is None

    @pytest.mark.asyncio
    async def test_find_by_token_hash_exists(
        self, db_session, repository, test_user, test_device
    ):
        """Test finding a token by hash when it exists."""
        chain_id = uuid4()
        token_hash = "unique_hash_123"

        token = RefreshToken(
            id=uuid4(),
            user_id=test_user.id,
            device_id=test_device.id,
            token_hash=token_hash,
            chain_id=chain_id,
            sequence_num=1,
            revoked_at=None,
            expires_at=datetime.now(UTC) + timedelta(days=90),
            created_at=datetime.now(UTC)
        )

        db_session.add(token)
        await db_session.flush()

        found = await repository.find_by_token_hash(db_session, token_hash)

        assert found is not None
        assert found.token_hash == token_hash
        assert found.chain_id == chain_id

    @pytest.mark.asyncio
    async def test_find_by_token_hash_not_exists(self, db_session, repository):
        """Test finding a token by hash when it doesn't exist."""
        found = await repository.find_by_token_hash(db_session, "nonexistent_hash")

        assert found is None

    @pytest.mark.asyncio
    async def test_revoke_single_token(
        self, db_session, repository, test_user, test_device
    ):
        """Test revoking a single token."""
        token_id = uuid4()
        token = RefreshToken(
            id=token_id,
            user_id=test_user.id,
            device_id=test_device.id,
            token_hash="hash_to_revoke",
            chain_id=uuid4(),
            sequence_num=1,
            revoked_at=None,
            expires_at=datetime.now(UTC) + timedelta(days=90),
            created_at=datetime.now(UTC)
        )

        db_session.add(token)
        await db_session.flush()

        # Revoke the token
        await repository.revoke(db_session, token_id)

        # Verify it's revoked by checking the field directly
        result = await db_session.execute(
            select(RefreshToken.revoked_at).where(RefreshToken.id == token_id)
        )
        revoked_at = result.scalar_one()

        assert revoked_at is not None
        assert isinstance(revoked_at, datetime)

    @pytest.mark.asyncio
    async def test_revoke_chain(
        self, db_session, repository, test_user, test_device
    ):
        """Test revoking all tokens in a chain."""
        chain_id = uuid4()

        # Create 3 tokens in the same chain
        for seq in [1, 2, 3]:
            token = RefreshToken(
                id=uuid4(),
                user_id=test_user.id,
                device_id=test_device.id,
                token_hash=f"hash_{seq}",
                chain_id=chain_id,
                sequence_num=seq,
                revoked_at=None,
                expires_at=datetime.now(UTC) + timedelta(days=90),
                created_at=datetime.now(UTC)
            )
            db_session.add(token)

        await db_session.flush()

        # Revoke the entire chain
        count = await repository.revoke_chain(db_session, chain_id)

        assert count == 3

        # Verify all tokens are revoked
        result = await db_session.execute(
            select(RefreshToken.revoked_at).where(RefreshToken.chain_id == chain_id)
        )
        revoked_ats = result.scalars().all()

        assert len(revoked_ats) == 3
        for revoked_at in revoked_ats:
            assert revoked_at is not None

    @pytest.mark.asyncio
    async def test_revoke_chain_with_already_revoked(
        self, db_session, repository, test_user, test_device
    ):
        """Test revoking a chain where some tokens are already revoked."""
        chain_id = uuid4()

        # Create 3 tokens, one already revoked
        for seq in [1, 2, 3]:
            token = RefreshToken(
                id=uuid4(),
                user_id=test_user.id,
                device_id=test_device.id,
                token_hash=f"hash_{seq}",
                chain_id=chain_id,
                sequence_num=seq,
                revoked_at=datetime.now(UTC) if seq == 1 else None,
                expires_at=datetime.now(UTC) + timedelta(days=90),
                created_at=datetime.now(UTC)
            )
            db_session.add(token)

        await db_session.flush()

        # Revoke the entire chain (should update all, including already revoked)
        count = await repository.revoke_chain(db_session, chain_id)

        assert count == 3

        # Verify all tokens are revoked
        result = await db_session.execute(
            select(RefreshToken.revoked_at).where(RefreshToken.chain_id == chain_id)
        )
        revoked_ats = result.scalars().all()

        assert len(revoked_ats) == 3
        for revoked_at in revoked_ats:
            assert revoked_at is not None

    @pytest.mark.asyncio
    async def test_revoke_chain_no_tokens(self, db_session, repository):
        """Test revoking a chain with no tokens returns 0."""
        nonexistent_chain = uuid4()

        count = await repository.revoke_chain(db_session, nonexistent_chain)
        await db_session.commit()

        assert count == 0
