"""Tests for FileStatus enum."""

import pytest

from app.shared.enums.file_status import FileStatus


def test_file_status_enum_has_all_required_values():
    """Test that FileStatus enum exports all required status values."""
    required_statuses = {
        "DISCOVERED",
        "PRE_REGISTERED",
        "UPLOADING",
        "PAUSED",
        "PAUSED_USER",
        "SYNCED",
        "FAILED",
        "CANCELLED",
    }

    actual_statuses = {status.value for status in FileStatus}
    assert actual_statuses == required_statuses, (
        f"FileStatus enum values mismatch. "
        f"Missing: {required_statuses - actual_statuses}, "
        f"Extra: {actual_statuses - required_statuses}"
    )


def test_file_status_enum_values_are_strings():
    """Test that all FileStatus enum values are strings matching their names."""
    for status in FileStatus:
        assert isinstance(status.value, str), f"{status.name} value is not a string"
        assert status.value == status.name, (
            f"{status.name} value '{status.value}' does not match name"
        )


def test_file_status_count():
    """Test that FileStatus enum has exactly 8 values."""
    assert len(FileStatus) == 8, f"Expected 8 statuses, got {len(FileStatus)}"
