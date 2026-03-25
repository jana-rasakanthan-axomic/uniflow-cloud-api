"""Tests for CommandRepository."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.command import Command
from app.repositories.command_repository import CommandRepository


@pytest.fixture
async def db_session():
    """Create in-memory SQLite database session for testing."""
    # Create async engine for SQLite
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session factory
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    # Yield session
    async with async_session() as session:
        yield session

    # Cleanup
    await engine.dispose()


@pytest.fixture
def agent_id() -> UUID:
    """Generate a test agent UUID."""
    return uuid4()


@pytest.fixture
def command_repository() -> CommandRepository:
    """Create CommandRepository instance."""
    return CommandRepository()


@pytest.mark.asyncio
async def test_pop_pending_returns_oldest_pending_command(
    db_session: AsyncSession,
    agent_id: UUID,
    command_repository: CommandRepository
):
    """Test pop_pending returns oldest PENDING command and marks it DELIVERED."""
    # Create multiple PENDING commands with different timestamps
    from datetime import timedelta
    now = datetime.now(UTC)

    # Older command (should be returned first)
    cmd1 = Command(
        agent_id=agent_id,
        type="SCAN",
        payload_json={"path": "/test1"},
        status="PENDING",
        created_at=now - timedelta(seconds=10)
    )

    # Newer command
    cmd2 = Command(
        agent_id=agent_id,
        type="STOP",
        payload_json={},
        status="PENDING",
        created_at=now
    )

    # Add commands out of order to verify ordering by created_at
    db_session.add(cmd2)
    db_session.add(cmd1)
    await db_session.commit()

    # Fetch oldest pending command
    result = await command_repository.pop_pending(db_session, agent_id)

    # Verify we got the oldest command
    assert result is not None
    assert result.id == cmd1.id
    assert result.type == "SCAN"
    assert result.payload_json == {"path": "/test1"}

    # Verify status changed to DELIVERED
    await db_session.refresh(result)
    assert result.status == "DELIVERED"
    assert result.delivered_at is not None

    # Verify the newer command is still PENDING
    await db_session.refresh(cmd2)
    assert cmd2.status == "PENDING"
    assert cmd2.delivered_at is None


@pytest.mark.asyncio
async def test_pop_pending_returns_none_when_no_pending(
    db_session: AsyncSession,
    agent_id: UUID,
    command_repository: CommandRepository
):
    """Test pop_pending returns None when no PENDING commands exist."""
    # Create a DELIVERED command
    cmd = Command(
        agent_id=agent_id,
        type="SCAN",
        payload_json={"path": "/test"},
        status="DELIVERED",
        delivered_at=datetime.now(UTC)
    )
    db_session.add(cmd)
    await db_session.commit()

    # Try to fetch pending command
    result = await command_repository.pop_pending(db_session, agent_id)

    # Should return None
    assert result is None


@pytest.mark.asyncio
async def test_pop_pending_returns_none_when_empty(
    db_session: AsyncSession,
    agent_id: UUID,
    command_repository: CommandRepository
):
    """Test pop_pending returns None when no commands exist at all."""
    # No commands in database
    result = await command_repository.pop_pending(db_session, agent_id)

    # Should return None
    assert result is None


@pytest.mark.asyncio
async def test_pop_pending_only_returns_commands_for_specified_agent(
    db_session: AsyncSession,
    agent_id: UUID,
    command_repository: CommandRepository
):
    """Test pop_pending only returns commands for the specified agent."""
    other_agent_id = uuid4()

    # Create PENDING command for a different agent
    cmd_other = Command(
        agent_id=other_agent_id,
        type="SCAN",
        payload_json={"path": "/other"},
        status="PENDING"
    )
    db_session.add(cmd_other)
    await db_session.commit()

    # Try to fetch pending command for our agent
    result = await command_repository.pop_pending(db_session, agent_id)

    # Should return None (no commands for this agent)
    assert result is None

    # Verify the other agent's command is still PENDING
    await db_session.refresh(cmd_other)
    assert cmd_other.status == "PENDING"


@pytest.mark.asyncio
async def test_pop_pending_ignores_expired_commands(
    db_session: AsyncSession,
    agent_id: UUID,
    command_repository: CommandRepository
):
    """Test pop_pending ignores EXPIRED commands."""
    # Create an EXPIRED command
    cmd_expired = Command(
        agent_id=agent_id,
        type="SCAN",
        payload_json={"path": "/expired"},
        status="EXPIRED"
    )

    # Create a PENDING command
    cmd_pending = Command(
        agent_id=agent_id,
        type="STOP",
        payload_json={},
        status="PENDING"
    )

    db_session.add(cmd_expired)
    db_session.add(cmd_pending)
    await db_session.commit()

    # Fetch pending command
    result = await command_repository.pop_pending(db_session, agent_id)

    # Should return the PENDING command, not the EXPIRED one
    assert result is not None
    assert result.id == cmd_pending.id
    assert result.status == "DELIVERED"
