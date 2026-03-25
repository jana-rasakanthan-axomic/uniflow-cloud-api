"""Upload request/response schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class STSCredentials(BaseModel):
    """AWS STS credentials for direct S3 upload."""

    access_key: str = Field(..., description="AWS access key ID")
    secret_key: str = Field(..., description="AWS secret access key")
    session_token: str = Field(..., description="AWS session token")
    expiry: datetime = Field(..., description="Token expiry timestamp")


class UploadTarget(BaseModel):
    """S3 upload target for a specific file."""

    file_id: UUID = Field(..., description="File UUID")
    bucket: str = Field(..., description="S3 bucket name")
    key: str = Field(..., description="S3 object key")
    oa_asset_id: str = Field(..., description="OpenAsset asset ID")


class STSRequest(BaseModel):
    """Request schema for POST /edge/upload/sts endpoint."""

    job_id: UUID = Field(..., description="Job UUID")
    file_ids: list[UUID] = Field(..., min_length=1, description="List of file UUIDs to upload")


class STSResponse(BaseModel):
    """Response schema for POST /edge/upload/sts endpoint."""

    credentials: STSCredentials = Field(..., description="Temporary AWS credentials")
    upload_targets: list[UploadTarget] = Field(..., description="S3 upload targets for each file")


class ProgressRequest(BaseModel):
    """Request schema for POST /edge/upload/progress endpoint."""

    job_id: UUID = Field(..., description="Job UUID")
    file_id: UUID = Field(..., description="File UUID")
    chunks_completed: int = Field(..., ge=0, description="Number of chunks completed")
    total_chunks: int = Field(..., ge=1, description="Total number of chunks")
    status: Literal["UPLOADING", "PAUSED", "SYNCED", "FAILED"] = Field(
        ..., description="Current file upload status"
    )
    streaming_hash: str | None = Field(None, description="SHA-256 hash computed during upload")
    error_message: str | None = Field(None, description="Error message if status is FAILED")


class ProgressResponse(BaseModel):
    """Response schema for POST /edge/upload/progress endpoint."""

    ack: bool = Field(..., description="Acknowledgment of progress update")
    file_status: str = Field(..., description="Current file status")
