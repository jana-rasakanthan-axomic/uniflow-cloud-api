"""Tests for status helper utilities including color mappings."""


from app.shared.constants.status_colors import STATUS_COLORS
from app.shared.enums.job_status import JobStatus
from app.shared.utils.status_helpers import get_status_color, get_status_explanation


def test_status_colors_constants_defined():
    """Test that all required color constants are defined."""
    required_colors = {"BLUE", "GREEN", "AMBER", "PURPLE", "RED", "GRAY"}
    actual_colors = set(STATUS_COLORS.keys())

    assert actual_colors == required_colors, (
        f"Color constants mismatch. "
        f"Missing: {required_colors - actual_colors}, "
        f"Extra: {actual_colors - required_colors}"
    )


def test_status_colors_values():
    """Test that color constants have correct hex values."""
    expected_values = {
        "BLUE": "#2563EB",
        "GREEN": "#16A34A",
        "AMBER": "#D97706",
        "PURPLE": "#9333EA",
        "RED": "#DC2626",
        "GRAY": "#6B7280",
    }

    for color, expected_hex in expected_values.items():
        assert STATUS_COLORS[color] == expected_hex, (
            f"Color {color} has wrong value: {STATUS_COLORS[color]} (expected {expected_hex})"
        )


def test_get_status_color_in_progress():
    """Test that IN_PROGRESS status maps to BLUE."""
    color = get_status_color(JobStatus.IN_PROGRESS)
    assert color == "#2563EB"


def test_get_status_color_completed():
    """Test that COMPLETED status maps to GREEN."""
    color = get_status_color(JobStatus.COMPLETED)
    assert color == "#16A34A"


def test_get_status_color_waiting_for_agent():
    """Test that WAITING_FOR_AGENT status maps to AMBER."""
    color = get_status_color(JobStatus.WAITING_FOR_AGENT)
    assert color == "#D97706"


def test_get_status_color_paused_user():
    """Test that PAUSED_USER status maps to PURPLE."""
    color = get_status_color(JobStatus.PAUSED_USER)
    assert color == "#9333EA"


def test_get_status_color_failed():
    """Test that FAILED status maps to RED."""
    color = get_status_color(JobStatus.FAILED)
    assert color == "#DC2626"


def test_get_status_color_denied():
    """Test that DENIED status maps to RED."""
    color = get_status_color(JobStatus.DENIED)
    assert color == "#DC2626"


def test_get_status_color_cancelled():
    """Test that CANCELLED status maps to RED."""
    color = get_status_color(JobStatus.CANCELLED)
    assert color == "#DC2626"


def test_get_status_color_offline():
    """Test that OFFLINE status maps to GRAY."""
    color = get_status_color(JobStatus.OFFLINE)
    assert color == "#6B7280"


def test_get_status_color_pre_registering():
    """Test that PRE_REGISTERING status maps to AMBER."""
    color = get_status_color(JobStatus.PRE_REGISTERING)
    assert color == "#D97706"


def test_get_status_color_partially_failed():
    """Test that PARTIALLY_FAILED status maps to AMBER."""
    color = get_status_color(JobStatus.PARTIALLY_FAILED)
    assert color == "#D97706"


def test_get_status_color_timeout():
    """Test that TIMEOUT status maps to RED."""
    color = get_status_color(JobStatus.TIMEOUT)
    assert color == "#DC2626"


# Explanation template tests


def test_explanation_waiting_for_agent():
    """Test explanation for WAITING_FOR_AGENT status."""
    result = get_status_explanation(
        JobStatus.WAITING_FOR_AGENT, {"deviceName": "MacBook", "expiryDays": 3}
    )

    assert "MacBook" in result["message"]
    assert "3" in result["message"] or "three" in result["message"].lower()
    assert "approve" in result["message"].lower() or "approval" in result["message"].lower()
    assert result["action"]  # Should have an action


def test_explanation_in_progress():
    """Test explanation for IN_PROGRESS status."""
    result = get_status_explanation(
        JobStatus.IN_PROGRESS, {"filesCompleted": 15, "filesTotal": 100}
    )

    assert "15" in result["message"] or "uploading" in result["message"].lower()
    assert "100" in result["message"]
    assert result["action"]


def test_explanation_paused_user():
    """Test explanation for PAUSED_USER status."""
    result = get_status_explanation(JobStatus.PAUSED_USER, {})

    assert "paused" in result["message"].lower()
    assert "you" in result["message"].lower() or "user" in result["message"].lower()
    assert "resume" in result["action"].lower()


def test_explanation_offline():
    """Test explanation for OFFLINE status."""
    result = get_status_explanation(JobStatus.OFFLINE, {"deviceName": "MacBook"})

    assert "offline" in result["message"].lower() or "unavailable" in result["message"].lower()
    assert result["action"]


def test_explanation_denied():
    """Test explanation for DENIED status."""
    result = get_status_explanation(JobStatus.DENIED, {"deviceName": "MacBook"})

    assert "denied" in result["message"].lower()
    assert "MacBook" in result["message"]
    assert result["action"]


def test_explanation_completed():
    """Test explanation for COMPLETED status."""
    result = get_status_explanation(JobStatus.COMPLETED, {"filesTotal": 100})

    assert "100" in result["message"]
    assert "success" in result["message"].lower() or "completed" in result["message"].lower()
    assert result["action"]


def test_explanation_failed():
    """Test explanation for FAILED status."""
    result = get_status_explanation(
        JobStatus.FAILED, {"filesCompleted": 75, "filesTotal": 100, "reason": "Network error"}
    )

    assert "failed" in result["message"].lower() or "error" in result["message"].lower()
    assert result["action"]


def test_explanation_pre_registering():
    """Test explanation for PRE_REGISTERING status."""
    result = get_status_explanation(JobStatus.PRE_REGISTERING, {})

    assert result["message"]
    assert result["action"]


def test_explanation_partially_failed():
    """Test explanation for PARTIALLY_FAILED status."""
    result = get_status_explanation(
        JobStatus.PARTIALLY_FAILED, {"filesCompleted": 75, "filesTotal": 100}
    )

    assert result["message"]
    assert result["action"]


def test_explanation_cancelled():
    """Test explanation for CANCELLED status."""
    result = get_status_explanation(JobStatus.CANCELLED, {})

    assert "cancel" in result["message"].lower()
    assert result["action"]


def test_explanation_timeout():
    """Test explanation for TIMEOUT status."""
    result = get_status_explanation(JobStatus.TIMEOUT, {})

    assert (
        "timeout" in result["message"].lower()
        or "timed out" in result["message"].lower()
        or "expired" in result["message"].lower()
    )
    assert result["action"]
