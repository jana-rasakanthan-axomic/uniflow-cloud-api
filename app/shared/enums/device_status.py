"""Device status enum for UniFlow.

This enum defines all possible states for an edge agent device in the UniFlow system.
Values must be kept in sync with TypeScript DeviceStatus enum in uniflow-edge and
uniflow-cloud-portal.
"""

from enum import Enum


class DeviceStatus(str, Enum):
    """Device status values shared across edge, portal, and cloud API."""

    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    SYNCING = "SYNCING"
    PAUSED = "PAUSED"
    ERROR = "ERROR"
