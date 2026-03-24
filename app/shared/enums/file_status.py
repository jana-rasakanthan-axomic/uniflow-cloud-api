"""File status enum for UniFlow.

This enum defines all possible states for an individual file in the UniFlow system.
Values must be kept in sync with TypeScript FileStatus enum in uniflow-edge and
uniflow-cloud-portal.
"""

from enum import Enum


class FileStatus(str, Enum):
    """File status values shared across edge, portal, and cloud API."""

    DISCOVERED = "DISCOVERED"
    PRE_REGISTERED = "PRE_REGISTERED"
    UPLOADING = "UPLOADING"
    PAUSED = "PAUSED"
    PAUSED_USER = "PAUSED_USER"
    SYNCED = "SYNCED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
