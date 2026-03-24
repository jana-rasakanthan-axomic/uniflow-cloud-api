"""Tests for file repository."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models.asset import Asset
from app.models.collection import Collection
from app.models.folder import Folder
from app.models.job import Job
from app.models.job_file import JobFile
from app.models.organization import Organization
from app.repositories.file_repository import FileRepository


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
        # Create only the tables we need (avoid JSONB tables like Command)
        await conn.run_sync(Organization.__table__.create)
        await conn.run_sync(User.__table__.create)
        await conn.run_sync(Device.__table__.create)
        await conn.run_sync(SetupCode.__table__.create)
        await conn.run_sync(Folder.__table__.create)
        await conn.run_sync(Asset.__table__.create)
        await conn.run_sync(Collection.__table__.create)
        await conn.run_sync(Job.__table__.create)
        await conn.run_sync(JobFile.__table__.create)

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
async def test_folder(db_session, test_org):
    """Create a test folder."""
    folder = Folder(
        id=uuid4(),
        org_id=test_org.id,
        path="/test/path",
        created_at=datetime.now(UTC)
    )
    db_session.add(folder)
    await db_session.commit()
    await db_session.refresh(folder)
    return folder


@pytest.fixture
async def test_assets(db_session, test_folder):
    """Create test assets."""
    assets = []
    for i in range(3):
        asset = Asset(
            id=uuid4(),
            folder_id=test_folder.id,
            filename=f"test_file_{i}.jpg",
            size_bytes=1024 * (i + 1),
            content_hash=f"hash_{i}",
            mime_type="image/jpeg",
            created_at=datetime.now(UTC)
        )
        db_session.add(asset)
        assets.append(asset)

    await db_session.commit()
    for asset in assets:
        await db_session.refresh(asset)
    return assets


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
async def test_job(db_session, test_org, test_collection):
    """Create a test job."""
    job = Job(
        id=uuid4(),
        org_id=test_org.id,
        collection_id=test_collection.id,
        status="PRE_REGISTERING",
        expires_at=datetime.now(UTC) + timedelta(days=7),
        created_at=datetime.now(UTC)
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job


@pytest.fixture
def file_repository():
    """Create file repository instance."""
    return FileRepository()


class TestFileRepository:
    """Test file repository CRUD operations."""

    async def test_bulk_create_job_files(
        self, db_session, file_repository, test_job, test_assets
    ):
        """Test bulk creating job_files in DISCOVERED state."""
        file_ids = [asset.id for asset in test_assets]

        job_files = await file_repository.bulk_create(
            db=db_session,
            job_id=test_job.id,
            asset_ids=file_ids,
            initial_status="DISCOVERED"
        )

        assert len(job_files) == 3
        for job_file in job_files:
            assert job_file.job_id == test_job.id
            assert job_file.asset_id in file_ids
            assert job_file.status == "DISCOVERED"
            assert job_file.oa_asset_id is None
            assert job_file.chunks_completed == 0
            assert job_file.total_chunks == 0

        # Verify in database
        result = await db_session.execute(
            select(JobFile).where(JobFile.job_id == test_job.id)
        )
        db_job_files = result.scalars().all()
        assert len(db_job_files) == 3

    async def test_update_file_status_to_pre_registered(
        self, db_session, file_repository, test_job, test_assets
    ):
        """Test updating file status to PRE_REGISTERED with oa_asset_id."""
        # Create initial job file
        job_files = await file_repository.bulk_create(
            db=db_session,
            job_id=test_job.id,
            asset_ids=[test_assets[0].id],
            initial_status="DISCOVERED"
        )
        await db_session.commit()

        job_file = job_files[0]
        oa_asset_id = "OA-12345"

        # Update status
        updated_file = await file_repository.update_status(
            db=db_session,
            job_file_id=job_file.id,
            new_status="PRE_REGISTERED",
            oa_asset_id=oa_asset_id
        )

        assert updated_file.id == job_file.id
        assert updated_file.status == "PRE_REGISTERED"
        assert updated_file.oa_asset_id == oa_asset_id

        # Verify in database
        await db_session.refresh(updated_file)
        assert updated_file.status == "PRE_REGISTERED"
        assert updated_file.oa_asset_id == oa_asset_id

    async def test_update_file_status_to_failed(
        self, db_session, file_repository, test_job, test_assets
    ):
        """Test updating file status to FAILED with error message."""
        # Create initial job file
        job_files = await file_repository.bulk_create(
            db=db_session,
            job_id=test_job.id,
            asset_ids=[test_assets[0].id],
            initial_status="DISCOVERED"
        )
        await db_session.commit()

        job_file = job_files[0]
        error_message = "OA API returned 500"

        # Update status
        updated_file = await file_repository.update_status(
            db=db_session,
            job_file_id=job_file.id,
            new_status="FAILED",
            error_message=error_message
        )

        assert updated_file.status == "FAILED"
        assert updated_file.error_message == error_message

        # Verify in database
        await db_session.refresh(updated_file)
        assert updated_file.status == "FAILED"
        assert updated_file.error_message == error_message

    async def test_find_by_job_id(
        self, db_session, file_repository, test_job, test_assets
    ):
        """Test finding all files for a job."""
        # Create job files
        await file_repository.bulk_create(
            db=db_session,
            job_id=test_job.id,
            asset_ids=[asset.id for asset in test_assets],
            initial_status="DISCOVERED"
        )
        await db_session.commit()

        # Find by job ID
        found_files = await file_repository.find_by_job_id(
            db=db_session,
            job_id=test_job.id
        )

        assert len(found_files) == 3
        for file in found_files:
            assert file.job_id == test_job.id
            assert file.status == "DISCOVERED"

    async def test_bulk_update_status(
        self, db_session, file_repository, test_job, test_assets
    ):
        """Test bulk updating status for multiple files."""
        # Create job files
        job_files = await file_repository.bulk_create(
            db=db_session,
            job_id=test_job.id,
            asset_ids=[asset.id for asset in test_assets],
            initial_status="DISCOVERED"
        )
        await db_session.commit()

        file_ids = [jf.id for jf in job_files[:2]]  # Update first 2 files

        # Bulk update
        await file_repository.bulk_update_status(
            db=db_session,
            job_file_ids=file_ids,
            new_status="PRE_REGISTERED"
        )

        # Verify updates
        updated_files = await file_repository.find_by_job_id(
            db=db_session,
            job_id=test_job.id
        )

        pre_registered_count = sum(
            1 for f in updated_files if f.status == "PRE_REGISTERED"
        )
        discovered_count = sum(
            1 for f in updated_files if f.status == "DISCOVERED"
        )

        assert pre_registered_count == 2
        assert discovered_count == 1
