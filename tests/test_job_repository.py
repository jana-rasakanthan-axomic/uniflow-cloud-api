"""Tests for job repository."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models.collection import Collection
from app.models.job import Job
from app.models.organization import Organization
from app.repositories.job_repository import JobRepository


@pytest.fixture
async def engine():
    """Create in-memory SQLite engine for testing."""
    from app.models.device import Device
    from app.models.setup_code import SetupCode
    from app.models.user import User

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    async with engine.begin() as conn:
        # Create only the tables we need (avoid JSONB tables like Command/Asset)
        await conn.run_sync(Organization.__table__.create)
        await conn.run_sync(User.__table__.create)
        await conn.run_sync(Device.__table__.create)
        await conn.run_sync(SetupCode.__table__.create)
        await conn.run_sync(Collection.__table__.create)
        await conn.run_sync(Job.__table__.create)
        # Note: Not creating JobFile table since Job relationship uses lazy="selectin"
        # but we'll disable relationship loading in tests

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
    """Create a test organization."""
    org = Organization(
        id=uuid4(),
        name="Test Organization",
        slug="test-org",
        job_timeout_days=7,
        created_at=datetime.now(UTC)
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest.fixture
async def test_collection(db_session, test_org):
    """Create a test collection."""
    collection = Collection(
        id=uuid4(),
        org_id=test_org.id,
        name="Test Collection",
        created_at=datetime.now(UTC)
    )
    db_session.add(collection)
    await db_session.commit()
    await db_session.refresh(collection)
    return collection


@pytest.fixture
def job_repository():
    """Create job repository instance."""
    return JobRepository()


class TestJobRepository:
    """Test job repository CRUD operations."""

    async def test_create_job_in_pre_registering_state(
        self, db_session, job_repository, test_org, test_collection
    ):
        """Test creating a job in PRE_REGISTERING state."""
        job_id = uuid4()
        expires_at = datetime.now(UTC) + timedelta(days=7)

        job = await job_repository.create(
            db=db_session,
            job_id=job_id,
            org_id=test_org.id,
            collection_id=test_collection.id,
            status="PRE_REGISTERING",
            expires_at=expires_at
        )

        assert job.id == job_id
        assert job.org_id == test_org.id
        assert job.collection_id == test_collection.id
        assert job.status == "PRE_REGISTERING"
        assert job.expires_at == expires_at
        assert job.completed_at is None
        assert job.created_at is not None

        # Verify in database
        result = await db_session.execute(
            select(Job).where(Job.id == job_id)
        )
        db_job = result.scalar_one_or_none()
        assert db_job is not None
        assert db_job.status == "PRE_REGISTERING"

    async def test_update_job_state_to_waiting(
        self, db_session, job_repository, test_org, test_collection
    ):
        """Test updating job state from PRE_REGISTERING to WAITING_FOR_AGENT."""
        job_id = uuid4()
        expires_at = datetime.now(UTC) + timedelta(days=7)

        # Create job in PRE_REGISTERING
        job = await job_repository.create(
            db=db_session,
            job_id=job_id,
            org_id=test_org.id,
            collection_id=test_collection.id,
            status="PRE_REGISTERING",
            expires_at=expires_at
        )
        await db_session.commit()

        # Update to WAITING_FOR_AGENT
        updated_job = await job_repository.update_state(
            db=db_session,
            job_id=job_id,
            new_status="WAITING_FOR_AGENT"
        )

        assert updated_job.id == job_id
        assert updated_job.status == "WAITING_FOR_AGENT"

        # Verify in database
        await db_session.refresh(updated_job)
        assert updated_job.status == "WAITING_FOR_AGENT"

    async def test_update_job_state_to_failed(
        self, db_session, job_repository, test_org, test_collection
    ):
        """Test updating job state to FAILED."""
        job_id = uuid4()
        expires_at = datetime.now(UTC) + timedelta(days=7)

        # Create job
        job = await job_repository.create(
            db=db_session,
            job_id=job_id,
            org_id=test_org.id,
            collection_id=test_collection.id,
            status="PRE_REGISTERING",
            expires_at=expires_at
        )
        await db_session.commit()

        # Update to FAILED
        updated_job = await job_repository.update_state(
            db=db_session,
            job_id=job_id,
            new_status="FAILED"
        )

        assert updated_job.status == "FAILED"

        # Verify in database
        await db_session.refresh(updated_job)
        assert updated_job.status == "FAILED"

    async def test_find_by_id(
        self, db_session, job_repository, test_org, test_collection
    ):
        """Test finding job by ID."""
        job_id = uuid4()
        expires_at = datetime.now(UTC) + timedelta(days=7)

        # Create job
        await job_repository.create(
            db=db_session,
            job_id=job_id,
            org_id=test_org.id,
            collection_id=test_collection.id,
            status="PRE_REGISTERING",
            expires_at=expires_at
        )
        await db_session.commit()

        # Find by ID
        found_job = await job_repository.find_by_id(db=db_session, job_id=job_id)

        assert found_job is not None
        assert found_job.id == job_id
        assert found_job.status == "PRE_REGISTERING"

    async def test_find_by_id_not_found(self, db_session, job_repository):
        """Test finding non-existent job returns None."""
        non_existent_id = uuid4()

        found_job = await job_repository.find_by_id(
            db=db_session,
            job_id=non_existent_id
        )

        assert found_job is None
