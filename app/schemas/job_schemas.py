"""Job request/response schemas."""

from uuid import UUID

from pydantic import BaseModel, Field, field_validator


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
