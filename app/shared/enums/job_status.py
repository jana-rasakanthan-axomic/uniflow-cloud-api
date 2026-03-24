"""Job status enum for UniFlow.

This enum defines all possible states for a job (upload batch) in the UniFlow system.
Values must be kept in sync with TypeScript JobStatus enum in uniflow-edge and uniflow-cloud-portal.
"""

from enum import Enum


class JobStatus(str, Enum):
    """Job status values shared across edge, portal, and cloud API."""

    PRE_REGISTERING = "PRE_REGISTERING"
    WAITING_FOR_AGENT = "WAITING_FOR_AGENT"
    IN_PROGRESS = "IN_PROGRESS"
    PAUSED_USER = "PAUSED_USER"
    COMPLETED = "COMPLETED"
    PARTIALLY_FAILED = "PARTIALLY_FAILED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    DENIED = "DENIED"
    TIMEOUT = "TIMEOUT"
    OFFLINE = "OFFLINE"
