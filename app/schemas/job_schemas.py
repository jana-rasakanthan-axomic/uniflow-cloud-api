"""Job request/response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.shared.enums.job_status import JobStatus


class CreateJobRequest(BaseModel):
    """Request schema for POST /jobs endpoint.

    Validates collection_id and file_ids for job creation.
    """

    collection_id: UUID = Field(
        ...,
        description="UUID of the collection to submit"
    )
    file_ids: list[UUID] = Field(
        ...,
        description="List of file UUIDs to include in the job"
    )

    @field_validator("file_ids")
    @classmethod
    def validate_file_ids_not_empty(cls, v: list[UUID]) -> list[UUID]:
        """Validate that file_ids list is not empty."""
        if not v or len(v) == 0:
            raise ValueError("file_ids must contain at least one file")
        return v


class JobResponse(BaseModel):
    """Response schema for job creation.

    Returns the created job's ID and initial status.
    """

    job_id: UUID = Field(
        ...,
        description="UUID of the created job"
    )
    status: str = Field(
        ...,
        description="Initial job status (typically PRE_REGISTERING)"
    )


class JobStateTransitionRequest(BaseModel):
    """Request schema for PATCH /jobs/{job_id}/state endpoint.

    Validates the action to be performed on the job.
    """

    action: str = Field(
        ...,
        description="Action to perform (e.g., 'consent', 'cancel', 'complete')"
    )

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        """Validate that action is one of the allowed actions."""
        valid_actions = {
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
        }
        if v not in valid_actions:
            raise ValueError(
                f"Invalid action: {v}. Must be one of: {', '.join(sorted(valid_actions))}"
            )
        return v


class JobStateTransitionResponse(BaseModel):
    """Response schema for successful state transition.

    Returns the job ID, new status, and transition timestamp.
    """

    job_id: UUID = Field(
        ...,
        description="UUID of the job"
    )
    status: JobStatus = Field(
        ...,
        description="New job status after transition"
    )
    transitioned_at: datetime = Field(
        ...,
        description="Timestamp when the transition occurred"
    )


class ConflictErrorResponse(BaseModel):
    """Response schema for 409 Conflict errors.

    Used when a state transition is not allowed.
    """

    detail: str = Field(
        ...,
        description="Human-readable error message"
    )
    current_state: JobStatus = Field(
        ...,
        description="Current job status"
    )
    attempted_action: str = Field(
        ...,
        description="Action that was attempted"
    )
