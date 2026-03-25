"""Tests for JobStatus enum."""


from app.shared.enums.job_status import JobStatus


def test_job_status_enum_has_all_required_values():
    """Test that JobStatus enum exports all required status values."""
    required_statuses = {
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
        "OFFLINE",
    }

    actual_statuses = {status.value for status in JobStatus}
    assert actual_statuses == required_statuses, (
        f"JobStatus enum values mismatch. "
        f"Missing: {required_statuses - actual_statuses}, "
        f"Extra: {actual_statuses - required_statuses}"
    )


def test_job_status_enum_values_are_strings():
    """Test that all JobStatus enum values are strings matching their names."""
    for status in JobStatus:
        assert isinstance(status.value, str), f"{status.name} value is not a string"
        assert status.value == status.name, (
            f"{status.name} value '{status.value}' does not match name"
        )


def test_job_status_count():
    """Test that JobStatus enum has exactly 11 values."""
    assert len(JobStatus) == 11, f"Expected 11 statuses, got {len(JobStatus)}"
