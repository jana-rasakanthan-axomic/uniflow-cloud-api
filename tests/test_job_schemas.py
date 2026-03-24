"""Tests for job schemas."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.job_schemas import CreateJobRequest, JobResponse


class TestCreateJobRequest:
    """Test CreateJobRequest validation."""

    def test_valid_request(self):
        """Test valid job creation request."""
        collection_id = uuid4()
        file_ids = [uuid4(), uuid4(), uuid4()]

        request = CreateJobRequest(
            collection_id=collection_id,
            file_ids=file_ids
        )

        assert request.collection_id == collection_id
        assert request.file_ids == file_ids
        assert len(request.file_ids) == 3

    def test_empty_file_ids_raises_error(self):
        """Test that empty file_ids list raises validation error."""
        collection_id = uuid4()

        with pytest.raises(ValidationError) as exc_info:
            CreateJobRequest(
                collection_id=collection_id,
                file_ids=[]
            )

        errors = exc_info.value.errors()
        assert any("file_ids" in str(error) for error in errors)

    def test_missing_collection_id_raises_error(self):
        """Test that missing collection_id raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            CreateJobRequest(file_ids=[uuid4()])

        errors = exc_info.value.errors()
        assert any("collection_id" in str(error) for error in errors)

    def test_missing_file_ids_raises_error(self):
        """Test that missing file_ids raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            CreateJobRequest(collection_id=uuid4())

        errors = exc_info.value.errors()
        assert any("file_ids" in str(error) for error in errors)

    def test_invalid_uuid_raises_error(self):
        """Test that invalid UUID format raises validation error."""
        with pytest.raises(ValidationError):
            CreateJobRequest(
                collection_id="not-a-uuid",
                file_ids=["also-not-a-uuid"]
            )


class TestJobResponse:
    """Test JobResponse schema."""

    def test_valid_response(self):
        """Test valid job response."""
        job_id = uuid4()
        status = "PRE_REGISTERING"

        response = JobResponse(
            job_id=job_id,
            status=status
        )

        assert response.job_id == job_id
        assert response.status == status

    def test_response_serialization(self):
        """Test response can be serialized to dict."""
        job_id = uuid4()
        status = "PRE_REGISTERING"

        response = JobResponse(
            job_id=job_id,
            status=status
        )

        data = response.model_dump()
        assert data["job_id"] == job_id
        assert data["status"] == status

    def test_missing_job_id_raises_error(self):
        """Test that missing job_id raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            JobResponse(status="PRE_REGISTERING")

        errors = exc_info.value.errors()
        assert any("job_id" in str(error) for error in errors)

    def test_missing_status_raises_error(self):
        """Test that missing status raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            JobResponse(job_id=uuid4())

        errors = exc_info.value.errors()
        assert any("status" in str(error) for error in errors)
