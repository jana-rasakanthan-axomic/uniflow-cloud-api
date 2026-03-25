"""Tests for job schemas (Pydantic models)."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.job_schemas import (
    ConflictErrorResponse,
    JobStateTransitionRequest,
    JobStateTransitionResponse,
)
from app.shared.enums.job_status import JobStatus


class TestJobStateTransitionRequest:
    """Test JobStateTransitionRequest schema."""

    def test_valid_action(self):
        """Valid action creates schema successfully."""
        request = JobStateTransitionRequest(action="consent")
        assert request.action == "consent"

    def test_all_valid_actions(self):
        """All valid action strings are accepted."""
        valid_actions = [
            "complete_registration",
            "fail",
            "consent",
            "deny",
            "cancel",
            "timeout",
            "pause",
            "complete",
            "partial_fail",
            "resume",
        ]
        for action in valid_actions:
            request = JobStateTransitionRequest(action=action)
            assert request.action == action

    def test_invalid_action_raises_validation_error(self):
        """Invalid action raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            JobStateTransitionRequest(action="invalid_action")

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "action" in str(errors[0])

    def test_empty_action_raises_validation_error(self):
        """Empty string action raises ValidationError."""
        with pytest.raises(ValidationError):
            JobStateTransitionRequest(action="")

    def test_missing_action_raises_validation_error(self):
        """Missing action field raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            JobStateTransitionRequest()  # type: ignore

        errors = exc_info.value.errors()
        assert any("action" in str(error) for error in errors)


class TestJobStateTransitionResponse:
    """Test JobStateTransitionResponse schema."""

    def test_valid_response(self):
        """Valid response creates schema successfully."""
        job_id = uuid4()
        now = datetime.now(timezone.utc)

        response = JobStateTransitionResponse(
            job_id=job_id,
            status=JobStatus.IN_PROGRESS,
            transitioned_at=now,
        )

        assert response.job_id == job_id
        assert response.status == JobStatus.IN_PROGRESS
        assert response.transitioned_at == now

    def test_all_job_statuses_accepted(self):
        """All JobStatus enum values are accepted."""
        job_id = uuid4()
        now = datetime.now(timezone.utc)

        for status in JobStatus:
            response = JobStateTransitionResponse(
                job_id=job_id,
                status=status,
                transitioned_at=now,
            )
            assert response.status == status

    def test_invalid_status_raises_validation_error(self):
        """Invalid status string raises ValidationError."""
        job_id = uuid4()
        now = datetime.now(timezone.utc)

        with pytest.raises(ValidationError) as exc_info:
            JobStateTransitionResponse(
                job_id=job_id,
                status="INVALID_STATUS",  # type: ignore
                transitioned_at=now,
            )

        errors = exc_info.value.errors()
        assert any("status" in str(error) for error in errors)

    def test_missing_fields_raise_validation_error(self):
        """Missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            JobStateTransitionResponse()  # type: ignore

        errors = exc_info.value.errors()
        # Should have errors for all 3 required fields
        assert len(errors) == 3


class TestConflictErrorResponse:
    """Test ConflictErrorResponse schema."""

    def test_valid_conflict_response(self):
        """Valid conflict response creates schema successfully."""
        response = ConflictErrorResponse(
            detail="Cannot perform 'cancel' from state 'COMPLETED'",
            current_state=JobStatus.COMPLETED,
            attempted_action="cancel",
        )

        assert response.detail == "Cannot perform 'cancel' from state 'COMPLETED'"
        assert response.current_state == JobStatus.COMPLETED
        assert response.attempted_action == "cancel"

    def test_all_states_and_actions_accepted(self):
        """All states and action combinations are accepted."""
        for status in JobStatus:
            response = ConflictErrorResponse(
                detail="Test error",
                current_state=status,
                attempted_action="test_action",
            )
            assert response.current_state == status
            assert response.attempted_action == "test_action"

    def test_missing_fields_raise_validation_error(self):
        """Missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ConflictErrorResponse()  # type: ignore

        errors = exc_info.value.errors()
        # Should have errors for all 3 required fields
        assert len(errors) == 3
