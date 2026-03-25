"""Tests for DeviceStatus enum."""


from app.shared.enums.device_status import DeviceStatus


def test_device_status_enum_has_all_required_values():
    """Test that DeviceStatus enum exports all required status values."""
    required_statuses = {
        "ONLINE",
        "OFFLINE",
        "SYNCING",
        "PAUSED",
        "ERROR",
    }

    actual_statuses = {status.value for status in DeviceStatus}
    assert actual_statuses == required_statuses, (
        f"DeviceStatus enum values mismatch. "
        f"Missing: {required_statuses - actual_statuses}, "
        f"Extra: {actual_statuses - required_statuses}"
    )


def test_device_status_enum_values_are_strings():
    """Test that all DeviceStatus enum values are strings matching their names."""
    for status in DeviceStatus:
        assert isinstance(status.value, str), f"{status.name} value is not a string"
        assert status.value == status.name, (
            f"{status.name} value '{status.value}' does not match name"
        )


def test_device_status_count():
    """Test that DeviceStatus enum has exactly 5 values."""
    assert len(DeviceStatus) == 5, f"Expected 5 statuses, got {len(DeviceStatus)}"
