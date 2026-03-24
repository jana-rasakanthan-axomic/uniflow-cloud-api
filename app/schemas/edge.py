"""Edge request/response schemas."""

from typing import Literal

from pydantic import BaseModel, Field


class StateReportRequest(BaseModel):
    """Request schema for POST /edge/state endpoint.

    Validates agent status and optional metadata for state reporting.
    """

    status: Literal["ONLINE", "OFFLINE"] = Field(
        ...,
        description="Device status (ONLINE or OFFLINE)"
    )
    metadata: dict | None = Field(
        None,
        description="Optional metadata (agent_version, disk_space, cpu_percent, memory_percent)"
    )


class StateReportResponse(BaseModel):
    """Response schema for POST /edge/state endpoint.

    Returns acknowledgment of state update.
    """

    ack: bool = Field(
        ...,
        description="Acknowledgment of successful state update"
    )
