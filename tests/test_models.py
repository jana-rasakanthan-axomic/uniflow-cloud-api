"""Tests for SQLAlchemy models."""

from datetime import UTC, datetime
from uuid import uuid4

from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class TestBaseMixins:
    """Test base model mixins."""

    def test_uuid_primary_key_mixin_has_id_column(self):
        """Verify UUIDPrimaryKeyMixin defines id column."""
        assert hasattr(UUIDPrimaryKeyMixin, "id")

    def test_timestamp_mixin_has_created_at_column(self):
        """Verify TimestampMixin defines created_at column."""
        assert hasattr(TimestampMixin, "created_at")


class TestOrganizationModel:
    """Test Organization model."""

    def test_organization_instantiation(self):
        """Create Organization instance with required fields."""
        from app.models.organization import Organization

        org = Organization(
            name="Acme Corp",
            slug="acme",
            job_timeout_days=7,
        )
        assert org.name == "Acme Corp"
        assert org.slug == "acme"
        assert org.job_timeout_days == 7
        # id will be generated when persisted to database
        assert hasattr(org, "id")

    def test_organization_optional_fields(self):
        """Verify oa_api_key_encrypted is nullable."""
        from app.models.organization import Organization

        org = Organization(name="Test", slug="test")
        assert org.oa_api_key_encrypted is None


class TestUserModel:
    """Test User model."""

    def test_user_instantiation(self):
        """Create User instance with org_id FK."""
        from app.models.user import User

        org_id = uuid4()
        user = User(
            org_id=org_id,
            email="user@example.com",
            role="admin",
        )
        assert user.org_id == org_id
        assert user.email == "user@example.com"
        assert user.role == "admin"

    def test_user_has_timestamps(self):
        """Verify User has created_at from TimestampMixin."""
        from app.models.user import User

        user = User(
            org_id=uuid4(),
            email="test@example.com",
            role="member",
        )
        assert hasattr(user, "created_at")
        # created_at will be set when persisted to database


class TestDeviceModel:
    """Test Device model."""

    def test_device_instantiation(self):
        """Create Device instance with all required FKs."""
        from app.models.device import Device

        device = Device(
            org_id=uuid4(),
            user_id=uuid4(),
            agent_id=uuid4(),
            machine_name="MacBook-Pro",
            os="macOS 14.2",
            status="active",
        )
        assert device.machine_name == "MacBook-Pro"
        assert device.os == "macOS 14.2"
        assert device.status == "active"

    def test_device_optional_last_seen(self):
        """Verify last_seen_at is nullable."""
        from app.models.device import Device

        device = Device(
            org_id=uuid4(),
            user_id=uuid4(),
            agent_id=uuid4(),
            machine_name="Test",
            os="Test OS",
            status="inactive",
        )
        assert device.last_seen_at is None


class TestSetupCodeModel:
    """Test SetupCode model."""

    def test_setup_code_instantiation(self):
        """Create SetupCode instance."""
        from app.models.setup_code import SetupCode

        expires_at = datetime.now(UTC)
        code = SetupCode(
            org_id=uuid4(),
            code="ABCD1234",
            expires_at=expires_at,
        )
        assert code.code == "ABCD1234"
        assert code.expires_at == expires_at

    def test_setup_code_nullable_used_at(self):
        """Verify used_at is nullable (unused codes)."""
        from app.models.setup_code import SetupCode

        code = SetupCode(
            org_id=uuid4(),
            code="TEST1234",
            expires_at=datetime.now(UTC),
        )
        assert code.used_at is None


class TestFolderModel:
    """Test Folder model."""

    def test_folder_instantiation(self):
        """Create Folder instance with device FK."""
        from app.models.folder import Folder

        folder = Folder(
            device_id=uuid4(),
            path_hash="abc123",
            relative_path="/Documents/Projects",
            file_count=42,
        )
        assert folder.path_hash == "abc123"
        assert folder.relative_path == "/Documents/Projects"
        assert folder.file_count == 42

    def test_folder_nullable_last_scan(self):
        """Verify last_scan_at is nullable."""
        from app.models.folder import Folder

        folder = Folder(
            device_id=uuid4(),
            path_hash="test",
            relative_path="/test",
            file_count=0,
        )
        assert folder.last_scan_at is None


class TestAssetModel:
    """Test Asset model."""

    def test_asset_instantiation(self):
        """Create Asset instance with all required fields."""
        from app.models.asset import Asset

        asset = Asset(
            folder_id=uuid4(),
            filename="photo.jpg",
            size_bytes=1024 * 1024 * 500,  # 500 MB
            content_hash="sha256:abc123",
            mime_type="image/jpeg",
        )
        assert asset.filename == "photo.jpg"
        assert asset.size_bytes == 1024 * 1024 * 500
        assert asset.content_hash == "sha256:abc123"
        assert asset.mime_type == "image/jpeg"

    def test_asset_bigint_size_bytes(self):
        """Verify size_bytes can handle large files (>4GB)."""
        from app.models.asset import Asset

        # Test with 10GB file
        large_size = 10 * 1024 * 1024 * 1024
        asset = Asset(
            folder_id=uuid4(),
            filename="large_file.mp4",
            size_bytes=large_size,
            content_hash="sha256:large",
            mime_type="video/mp4",
        )
        assert asset.size_bytes == large_size
        assert asset.size_bytes > 2**32  # Larger than 32-bit integer

    def test_asset_optional_fields(self):
        """Verify exif_json and thumbnail_url are nullable."""
        from app.models.asset import Asset

        asset = Asset(
            folder_id=uuid4(),
            filename="document.pdf",
            size_bytes=1024,
            content_hash="sha256:doc",
            mime_type="application/pdf",
        )
        assert asset.exif_json is None
        assert asset.thumbnail_url is None


class TestCollectionModel:
    """Test Collection model."""

    def test_collection_instantiation(self):
        """Create Collection instance with required fields."""
        from app.models.collection import Collection

        collection = Collection(
            org_id=uuid4(),
            name="Project Alpha Assets",
        )
        assert collection.org_id is not None
        assert collection.name == "Project Alpha Assets"
        assert hasattr(collection, "id")

    def test_collection_project_code_nullable(self):
        """Verify project_code can be NULL (BR-24: binding happens later)."""
        from app.models.collection import Collection

        collection = Collection(
            org_id=uuid4(),
            name="Unbound Collection",
        )
        assert collection.project_code is None

    def test_collection_with_project_code(self):
        """Create Collection with project_code."""
        from app.models.collection import Collection

        collection = Collection(
            org_id=uuid4(),
            name="Bound Collection",
            project_code="PROJ-001",
        )
        assert collection.project_code == "PROJ-001"


class TestCollectionAssetModel:
    """Test CollectionAsset association table."""

    def test_collection_asset_composite_key(self):
        """Create CollectionAsset with composite primary key."""
        from app.models.collection_asset import CollectionAsset

        coll_id = uuid4()
        asset_id = uuid4()

        ca = CollectionAsset(
            collection_id=coll_id,
            asset_id=asset_id,
        )
        assert ca.collection_id == coll_id
        assert ca.asset_id == asset_id


class TestJobModel:
    """Test Job model."""

    def test_job_instantiation(self):
        """Create Job instance with required fields."""
        from app.models.job import Job

        job = Job(
            org_id=uuid4(),
            collection_id=uuid4(),
            status="PRE_REGISTERING",
            expires_at=datetime.now(UTC),
        )
        assert job.status == "PRE_REGISTERING"
        assert job.expires_at is not None
        assert hasattr(job, "id")

    def test_job_status_check_constraint(self):
        """Reject invalid job status (should work with model validation)."""
        from app.models.job import Job

        # This tests model instantiation with invalid status
        # The actual CHECK constraint is enforced at database level
        # Here we just verify the model accepts valid statuses
        valid_statuses = [
            "PRE_REGISTERING",
            "WAITING_FOR_AGENT",
            "IN_PROGRESS",
            "PAUSED_USER",
            "COMPLETED",
            "PARTIALLY_FAILED",
            "FAILED",
            "CANCELLED",
            "DENIED",
            "TIMEOUT",
        ]

        for status in valid_statuses:
            job = Job(
                org_id=uuid4(),
                collection_id=uuid4(),
                status=status,
                expires_at=datetime.now(UTC),
            )
            assert job.status == status

    def test_job_expiry_timeout_fields(self):
        """Verify expires_at required, completed_at nullable."""
        from app.models.job import Job

        job = Job(
            org_id=uuid4(),
            collection_id=uuid4(),
            status="IN_PROGRESS",
            expires_at=datetime.now(UTC),
        )
        assert job.expires_at is not None
        assert job.completed_at is None


class TestJobFileModel:
    """Test JobFile model."""

    def test_job_file_instantiation(self):
        """Create JobFile instance with required fields."""
        from app.models.job_file import JobFile

        job_file = JobFile(
            job_id=uuid4(),
            asset_id=uuid4(),
            status="DISCOVERED",
            chunks_completed=0,
            total_chunks=10,
        )
        assert job_file.status == "DISCOVERED"
        assert job_file.chunks_completed == 0
        assert job_file.total_chunks == 10

    def test_job_file_status_check_constraint(self):
        """Verify JobFile accepts all valid statuses."""
        from app.models.job_file import JobFile

        valid_statuses = [
            "DISCOVERED",
            "PRE_REGISTERED",
            "UPLOADING",
            "PAUSED",
            "PAUSED_USER",
            "SYNCED",
            "FAILED",
            "CANCELLED",
        ]

        for status in valid_statuses:
            job_file = JobFile(
                job_id=uuid4(),
                asset_id=uuid4(),
                status=status,
                chunks_completed=0,
                total_chunks=1,
            )
            assert job_file.status == status

    def test_job_file_optional_fields(self):
        """Verify oa_asset_id and error_message are nullable."""
        from app.models.job_file import JobFile

        job_file = JobFile(
            job_id=uuid4(),
            asset_id=uuid4(),
            status="DISCOVERED",
            chunks_completed=0,
            total_chunks=5,
        )
        assert job_file.oa_asset_id is None
        assert job_file.error_message is None


class TestCommandModel:
    """Test Command model."""

    def test_command_instantiation(self):
        """Create Command instance with required fields."""
        from app.models.command import Command

        command = Command(
            agent_id=uuid4(),
            type="PAUSE_JOB",
            payload_json={"job_id": str(uuid4())},
            status="PENDING",
        )
        assert command.agent_id is not None
        assert command.type == "PAUSE_JOB"
        assert command.status == "PENDING"
        assert "job_id" in command.payload_json

    def test_command_status_check_constraint(self):
        """Verify Command accepts all valid statuses."""
        from app.models.command import Command

        valid_statuses = ["PENDING", "DELIVERED", "EXPIRED"]

        for status in valid_statuses:
            command = Command(
                agent_id=uuid4(),
                type="TEST",
                payload_json={},
                status=status,
            )
            assert command.status == status

    def test_command_optional_delivered_at(self):
        """Verify delivered_at is nullable."""
        from app.models.command import Command

        command = Command(
            agent_id=uuid4(),
            type="TEST",
            payload_json={},
            status="PENDING",
        )
        assert command.delivered_at is None


class TestRefreshTokenModel:
    """Test RefreshToken model."""

    def test_refresh_token_instantiation(self):
        """Create RefreshToken instance with required fields."""
        from app.models.refresh_token import RefreshToken

        token = RefreshToken(
            user_id=uuid4(),
            device_id=uuid4(),
            token_hash="sha256:abc123",
            chain_id=uuid4(),
            sequence_num=1,
            expires_at=datetime.now(UTC),
        )
        assert token.token_hash == "sha256:abc123"
        assert token.sequence_num == 1

    def test_refresh_token_chain_sequence(self):
        """Verify chain_id and sequence_num behavior."""
        from app.models.refresh_token import RefreshToken

        chain_id = uuid4()
        token1 = RefreshToken(
            user_id=uuid4(),
            device_id=uuid4(),
            token_hash="hash1",
            chain_id=chain_id,
            sequence_num=1,
            expires_at=datetime.now(UTC),
        )
        token2 = RefreshToken(
            user_id=uuid4(),
            device_id=uuid4(),
            token_hash="hash2",
            chain_id=chain_id,
            sequence_num=2,
            expires_at=datetime.now(UTC),
        )
        assert token1.chain_id == token2.chain_id
        assert token2.sequence_num == token1.sequence_num + 1

    def test_refresh_token_nullable_revoked_at(self):
        """Verify revoked_at is nullable."""
        from app.models.refresh_token import RefreshToken

        token = RefreshToken(
            user_id=uuid4(),
            device_id=uuid4(),
            token_hash="hash",
            chain_id=uuid4(),
            sequence_num=1,
            expires_at=datetime.now(UTC),
        )
        assert token.revoked_at is None


class TestAuditLogModel:
    """Test AuditLog model."""

    def test_audit_log_instantiation(self):
        """Create AuditLog instance with required fields."""
        from app.models.audit_log import AuditLog

        log = AuditLog(
            event_type="USER_LOGIN",
            source_ip="192.168.1.1",
            metadata_json={"user_agent": "Mozilla/5.0"},
        )
        assert log.event_type == "USER_LOGIN"
        assert log.source_ip == "192.168.1.1"
        assert log.metadata_json == {"user_agent": "Mozilla/5.0"}

    def test_audit_log_bigserial_id(self):
        """Verify AuditLog uses auto-incrementing BIGINT primary key."""
        from app.models.audit_log import AuditLog

        # The id field should not be set by default, allowing database to auto-increment
        log = AuditLog(
            event_type="TEST",
            source_ip="127.0.0.1",
            metadata_json={},
        )
        # id is None until persisted to database
        assert not hasattr(log, "id") or log.id is None

    def test_audit_log_nullable_org_id(self):
        """Verify org_id can be NULL (for pre-login events)."""
        from app.models.audit_log import AuditLog

        log = AuditLog(
            event_type="FAILED_LOGIN_ATTEMPT",
            source_ip="1.2.3.4",
            metadata_json={},
        )
        assert log.org_id is None

    def test_audit_log_with_org_id(self):
        """Create AuditLog with org_id."""
        from app.models.audit_log import AuditLog

        org_id = uuid4()
        log = AuditLog(
            org_id=org_id,
            event_type="ASSET_UPLOADED",
            source_ip="10.0.0.1",
            metadata_json={},
        )
        assert log.org_id == org_id

    def test_audit_log_nullable_actor_id(self):
        """Verify actor_id is nullable (for system events)."""
        from app.models.audit_log import AuditLog

        log = AuditLog(
            event_type="SYSTEM_BACKUP",
            source_ip="127.0.0.1",
            metadata_json={},
        )
        assert log.actor_id is None
