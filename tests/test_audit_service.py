"""Tests for audit service."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.audit_log import AuditLog
from app.services.audit_service import AuditService


@pytest.fixture
def audit_service():
    """Create audit service instance."""
    return AuditService()


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    session = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def test_org_id():
    """Test organization UUID."""
    return uuid4()


@pytest.fixture
def test_agent_id():
    """Test agent UUID."""
    return uuid4()


class TestAuditService:
    """Test audit service for immutable event logging."""

    async def test_log_device_linked_event(
        self, audit_service, mock_db_session, test_org_id, test_agent_id
    ):
        """Test logging a successful device link event."""
        await audit_service.log_event(
            db=mock_db_session,
            org_id=test_org_id,
            event_type="DEVICE_LINKED",
            actor_id=test_agent_id,
            source_ip="192.168.1.100",
            metadata={
                "machine_name": "John's MacBook Pro",
                "os": "macOS 14.2",
                "setup_code": "****ABCD"
            }
        )

        # Verify db.add was called with an AuditLog instance
        mock_db_session.add.assert_called_once()
        event = mock_db_session.add.call_args[0][0]

        assert isinstance(event, AuditLog)
        assert event.org_id == test_org_id
        assert event.event_type == "DEVICE_LINKED"
        assert event.actor_id == test_agent_id
        assert event.source_ip == "192.168.1.100"
        assert event.metadata_json["machine_name"] == "John's MacBook Pro"
        assert event.metadata_json["os"] == "macOS 14.2"
        assert event.metadata_json["setup_code"] == "****ABCD"
        assert event.created_at is not None

    async def test_log_link_code_failed_event(
        self, audit_service, mock_db_session
    ):
        """Test logging a failed setup code validation event."""
        await audit_service.log_event(
            db=mock_db_session,
            org_id=None,  # Unknown until code is validated
            event_type="LINK_CODE_FAILED",
            actor_id=None,
            source_ip="192.168.1.100",
            metadata={
                "setup_code_partial": "****WXYZ",
                "failure_reason": "EXPIRED",
                "machine_name": "Test Machine"
            }
        )

        # Verify event was created correctly
        event = mock_db_session.add.call_args[0][0]

        assert event.org_id is None
        assert event.event_type == "LINK_CODE_FAILED"
        assert event.actor_id is None
        assert event.source_ip == "192.168.1.100"
        assert event.metadata_json["setup_code_partial"] == "****WXYZ"
        assert event.metadata_json["failure_reason"] == "EXPIRED"

    async def test_log_event_with_empty_metadata(
        self, audit_service, mock_db_session, test_org_id
    ):
        """Test logging event with empty metadata dictionary."""
        await audit_service.log_event(
            db=mock_db_session,
            org_id=test_org_id,
            event_type="TEST_EVENT",
            actor_id=None,
            source_ip="127.0.0.1",
            metadata={}
        )

        event = mock_db_session.add.call_args[0][0]
        assert event.metadata_json == {}

    async def test_log_event_created_at_timestamp(
        self, audit_service, mock_db_session, test_org_id
    ):
        """Test that created_at timestamp is set automatically."""
        before = datetime.now(UTC)

        await audit_service.log_event(
            db=mock_db_session,
            org_id=test_org_id,
            event_type="TEST_EVENT",
            actor_id=None,
            source_ip="127.0.0.1",
            metadata={}
        )

        after = datetime.now(UTC)

        event = mock_db_session.add.call_args[0][0]

        # Verify timestamp is between before and after
        assert before <= event.created_at <= after

    async def test_audit_service_is_insert_only(self, audit_service):
        """Test that audit service only has insert methods, no update/delete."""
        # Verify no update or delete methods exist
        assert not hasattr(audit_service, "update_event")
        assert not hasattr(audit_service, "delete_event")
        assert not hasattr(audit_service, "modify_event")

        # Only log_event should exist
        assert hasattr(audit_service, "log_event")

    async def test_service_does_not_commit(
        self, audit_service, mock_db_session, test_org_id
    ):
        """Test that log_event does not commit the transaction."""
        await audit_service.log_event(
            db=mock_db_session,
            org_id=test_org_id,
            event_type="TEST_EVENT",
            actor_id=None,
            source_ip="127.0.0.1",
            metadata={}
        )

        # Verify commit was NOT called
        mock_db_session.commit.assert_not_called()

    async def test_multiple_events_can_be_logged(
        self, audit_service, mock_db_session, test_org_id
    ):
        """Test logging multiple events in sequence."""
        # Log first event
        await audit_service.log_event(
            db=mock_db_session,
            org_id=test_org_id,
            event_type="EVENT_1",
            actor_id=None,
            source_ip="127.0.0.1",
            metadata={"seq": 1}
        )

        # Log second event
        await audit_service.log_event(
            db=mock_db_session,
            org_id=test_org_id,
            event_type="EVENT_2",
            actor_id=None,
            source_ip="127.0.0.1",
            metadata={"seq": 2}
        )

        # Verify both calls to add
        assert mock_db_session.add.call_count == 2
