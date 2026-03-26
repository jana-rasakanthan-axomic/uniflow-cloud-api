"""Tests for SignalingService long-poll functionality."""

import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.command import Command
from app.services.signaling_service import SignalingService


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
def signaling_service() -> SignalingService:
    """Create SignalingService instance."""
    return SignalingService()


@pytest.mark.asyncio
async def test_hold_poll_returns_none_on_timeout(
    db_session: AsyncSession,
    agent_id: UUID,
    signaling_service: SignalingService
):
    """Test hold_poll returns None when timeout expires with no commands."""
    # Use very short timeout for testing
    result = await signaling_service.hold_poll(db_session, agent_id, timeout=0.1)

    # Should return None after timeout
    assert result is None


@pytest.mark.asyncio
async def test_hold_poll_returns_immediately_if_pending_command_exists(
    db_session: AsyncSession,
    agent_id: UUID,
    signaling_service: SignalingService
):
    """Test hold_poll returns immediately if a PENDING command exists."""
    # Create a PENDING command
    cmd = Command(
        agent_id=agent_id,
        type="SCAN",
        payload_json={"path": "/test"},
        status="PENDING"
    )
    db_session.add(cmd)
    await db_session.commit()

    # Call hold_poll - should return immediately
    start = datetime.now(UTC)
    result = await signaling_service.hold_poll(db_session, agent_id, timeout=10.0)
    elapsed = (datetime.now(UTC) - start).total_seconds()

    # Should return the command
    assert result is not None
    assert result.id == cmd.id
    assert result.status == "DELIVERED"

    # Should return quickly (under 1 second)
    assert elapsed < 1.0


@pytest.mark.asyncio
async def test_hold_poll_returns_command_when_dispatched(
    db_session: AsyncSession,
    agent_id: UUID,
    signaling_service: SignalingService
):
    """Test hold_poll returns command when dispatch_command is called."""
    # Create a PENDING command
    cmd = Command(
        agent_id=agent_id,
        type="STOP",
        payload_json={},
        status="PENDING"
    )
    db_session.add(cmd)
    await db_session.commit()

    # Start hold_poll in a background task
    async def poll_task():
        return await signaling_service.hold_poll(db_session, agent_id, timeout=5.0)

    task = asyncio.create_task(poll_task())

    # Wait a bit to ensure poll is active
    await asyncio.sleep(0.05)

    # Dispatch command to wake the poll
    await signaling_service.dispatch_command(db_session, agent_id)

    # Wait for task to complete
    result = await task

    # Should return the command
    assert result is not None
    assert result.id == cmd.id
    assert result.status == "DELIVERED"


@pytest.mark.asyncio
async def test_dispatch_command_to_non_polling_agent_does_nothing(
    db_session: AsyncSession,
    agent_id: UUID,
    signaling_service: SignalingService
):
    """Test dispatch_command does nothing if no active poll for agent."""
    # Create a PENDING command
    cmd = Command(
        agent_id=agent_id,
        type="SCAN",
        payload_json={"path": "/test"},
        status="PENDING"
    )
    db_session.add(cmd)
    await db_session.commit()

    # Dispatch to an agent that's not polling (should not raise error)
    await signaling_service.dispatch_command(db_session, agent_id)

    # Command should still be PENDING
    await db_session.refresh(cmd)
    assert cmd.status == "PENDING"


@pytest.mark.asyncio
async def test_hold_poll_cleans_up_event_after_timeout(
    db_session: AsyncSession,
    agent_id: UUID,
    signaling_service: SignalingService
):
    """Test hold_poll removes event from tracking after timeout."""
    # Start poll with short timeout
    result = await signaling_service.hold_poll(db_session, agent_id, timeout=0.1)

    # Should return None
    assert result is None

    # Event should be cleaned up (not in _poll_events)
    assert agent_id not in signaling_service._poll_events


@pytest.mark.asyncio
async def test_hold_poll_cleans_up_event_after_dispatch(
    db_session: AsyncSession,
    agent_id: UUID,
    signaling_service: SignalingService
):
    """Test hold_poll removes event from tracking after dispatch."""
    # Create a PENDING command
    cmd = Command(
        agent_id=agent_id,
        type="SCAN",
        payload_json={"path": "/test"},
        status="PENDING"
    )
    db_session.add(cmd)
    await db_session.commit()

    # Start hold_poll in background
    async def poll_task():
        return await signaling_service.hold_poll(db_session, agent_id, timeout=5.0)

    task = asyncio.create_task(poll_task())

    # Wait for poll to be active
    await asyncio.sleep(0.05)

    # Dispatch command
    await signaling_service.dispatch_command(db_session, agent_id)

    # Wait for completion
    result = await task

    # Should return command
    assert result is not None

    # Event should be cleaned up
    assert agent_id not in signaling_service._poll_events


@pytest.mark.asyncio
async def test_get_active_poll_agents_returns_currently_polling_agents(
    db_session: AsyncSession,
    agent_id: UUID,
    signaling_service: SignalingService
):
    """Test get_active_poll_agents returns set of currently polling agents."""
    # Initially no active polls
    active = signaling_service.get_active_poll_agents()
    assert len(active) == 0

    # Start a poll in background
    async def poll_task():
        return await signaling_service.hold_poll(db_session, agent_id, timeout=2.0)

    task = asyncio.create_task(poll_task())

    # Wait for poll to be active
    await asyncio.sleep(0.05)

    # Should show as active
    active = signaling_service.get_active_poll_agents()
    assert agent_id in active

    # Cancel the task to clean up
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_close_all_connections_wakes_all_polls(
    db_session: AsyncSession,
    signaling_service: SignalingService
):
    """Test close_all_connections wakes all held poll connections."""
    agent_id_1 = uuid4()
    agent_id_2 = uuid4()

    # Start two polls in background
    async def poll_task(agent_id: UUID):
        return await signaling_service.hold_poll(db_session, agent_id, timeout=5.0)

    task1 = asyncio.create_task(poll_task(agent_id_1))
    task2 = asyncio.create_task(poll_task(agent_id_2))

    # Wait for polls to be active
    await asyncio.sleep(0.05)

    # Close all connections
    await signaling_service.close_all_connections()

    # Both tasks should complete (returning None since no commands)
    result1 = await task1
    result2 = await task2

    assert result1 is None
    assert result2 is None

    # All events should be cleaned up
    assert len(signaling_service._poll_events) == 0


@pytest.mark.asyncio
async def test_hold_poll_updates_active_poll_set(
    db_session: AsyncSession,
    agent_id: UUID,
    signaling_service: SignalingService
):
    """Test hold_poll adds agent to active_poll_agent_ids during poll."""
    # Initially not in active set (deprecated field for backwards compat)
    assert agent_id not in signaling_service.active_poll_agent_ids

    # Start poll in background
    async def poll_task():
        return await signaling_service.hold_poll(db_session, agent_id, timeout=2.0)

    task = asyncio.create_task(poll_task())

    # Wait for poll to be active
    await asyncio.sleep(0.05)

    # Should be in active set
    assert agent_id in signaling_service.active_poll_agent_ids

    # Cancel and cleanup
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # After poll ends, should be removed from active set
    await asyncio.sleep(0.05)
    assert agent_id not in signaling_service.active_poll_agent_ids
