"""Status helper utilities for color mapping and explanations.

Provides functions to map status enum values to semantic colors and
human-readable explanation templates.
"""

from typing import Any

from app.shared.constants.status_colors import STATUS_COLORS
from app.shared.enums.job_status import JobStatus


def get_status_color(status: JobStatus) -> str:
    """Get the semantic color for a given job status.

    Args:
        status: The job status enum value

    Returns:
        Hex color code (e.g., "#2563EB")

    Color mappings:
        - BLUE: IN_PROGRESS (actively processing)
        - GREEN: COMPLETED (successfully finished)
        - AMBER: WAITING_FOR_AGENT, PRE_REGISTERING, PARTIALLY_FAILED (pending/incomplete)
        - PURPLE: PAUSED_USER (intentionally paused by user)
        - RED: FAILED, DENIED, CANCELLED, TIMEOUT (error states)
        - GRAY: OFFLINE (device unavailable)
    """
    color_mapping = {
        JobStatus.IN_PROGRESS: STATUS_COLORS["BLUE"],
        JobStatus.COMPLETED: STATUS_COLORS["GREEN"],
        JobStatus.WAITING_FOR_AGENT: STATUS_COLORS["AMBER"],
        JobStatus.PRE_REGISTERING: STATUS_COLORS["AMBER"],
        JobStatus.PARTIALLY_FAILED: STATUS_COLORS["AMBER"],
        JobStatus.PAUSED_USER: STATUS_COLORS["PURPLE"],
        JobStatus.FAILED: STATUS_COLORS["RED"],
        JobStatus.DENIED: STATUS_COLORS["RED"],
        JobStatus.CANCELLED: STATUS_COLORS["RED"],
        JobStatus.TIMEOUT: STATUS_COLORS["RED"],
        JobStatus.OFFLINE: STATUS_COLORS["GRAY"],
    }

    return color_mapping[status]


def get_status_explanation(status: JobStatus, context: dict[str, Any]) -> dict[str, str]:
    """Get human-readable explanation for a job status.

    Args:
        status: The job status enum value
        context: Context dict with optional keys:
            - deviceName: str - Name of the device
            - expiryDays: int - Days until expiry
            - filesCompleted: int - Number of files completed
            - filesTotal: int - Total number of files
            - reason: str - Reason for failure/issue

    Returns:
        Dict with "message" and "action" keys

    Example:
        >>> get_status_explanation(
        ...     JobStatus.WAITING_FOR_AGENT,
        ...     {"deviceName": "MacBook", "expiryDays": 3}
        ... )
        {
            "message": "Waiting for MacBook to approve. Expires in 3 days.",
            "action": "Wait for device approval or cancel request."
        }
    """
    device_name = context.get("deviceName", "Device")
    expiry_days = context.get("expiryDays", 0)
    files_completed = context.get("filesCompleted", 0)
    files_total = context.get("filesTotal", 0)
    reason = context.get("reason", "Unknown error")

    explanations = {
        JobStatus.PRE_REGISTERING: {
            "message": "Preparing files for upload...",
            "action": "Please wait while we register your files.",
        },
        JobStatus.WAITING_FOR_AGENT: {
            "message": f"Waiting for {device_name} to approve. Expires in {expiry_days} days.",
            "action": "Wait for device approval or cancel request.",
        },
        JobStatus.IN_PROGRESS: {
            "message": f"Uploading {files_completed} of {files_total} files...",
            "action": "Upload in progress. You can pause or cancel.",
        },
        JobStatus.PAUSED_USER: {
            "message": "Paused by you. Click Resume to continue.",
            "action": "Click Resume to continue upload.",
        },
        JobStatus.COMPLETED: {
            "message": f"All {files_total} files uploaded successfully.",
            "action": "Job complete. Files are now available in OpenAsset.",
        },
        JobStatus.PARTIALLY_FAILED: {
            "message": f"{files_completed} of {files_total} files uploaded. Some files failed.",
            "action": "Review failed files and retry if needed.",
        },
        JobStatus.FAILED: {
            "message": f"Upload failed. {reason}",
            "action": "Check error details and try again.",
        },
        JobStatus.CANCELLED: {
            "message": "Upload cancelled by you.",
            "action": "You can start a new upload anytime.",
        },
        JobStatus.DENIED: {
            "message": f"Denied by {device_name}. They must re-initiate.",
            "action": "Contact device owner to restart upload.",
        },
        JobStatus.TIMEOUT: {
            "message": "Request timed out. Device did not respond.",
            "action": "Check device connectivity and try again.",
        },
        JobStatus.OFFLINE: {
            "message": "Device is offline. Uploads will resume when it reconnects.",
            "action": "Ensure device is online and connected.",
        },
    }

    return explanations[status]
