"""Edge router - Agent-facing endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_agent_id_from_jwt
from app.config import settings
from app.database import get_db
from app.middleware.rate_limit_dependency import check_edge_rate_limit
from app.schemas.edge import StateReportRequest, StateReportResponse
from app.services.device_service import DeviceService
from app.services.signaling_service import SignalingService
from app.shared.enums import DeviceStatus

router = APIRouter(dependencies=[Depends(check_edge_rate_limit)])


@router.post("/heartbeat")
async def heartbeat():
    """Placeholder heartbeat endpoint."""
    return {"message": "Heartbeat endpoint - to be implemented"}


@router.post("/state", response_model=StateReportResponse)
async def report_state(
    state: StateReportRequest,
    agent_id: UUID = Depends(get_agent_id_from_jwt),
    db: AsyncSession = Depends(get_db)
) -> StateReportResponse:
    """Report agent state (ONLINE/OFFLINE) with optional metadata.

    Args:
        state: State report request with status and metadata
        agent_id: Device agent UUID extracted from JWT
        db: Database session

    Returns:
        Acknowledgment response

    Raises:
        HTTPException: 401 if JWT is invalid
    """
    # Parse status from request
    status = DeviceStatus.ONLINE if state.status == "ONLINE" else DeviceStatus.OFFLINE

    # Update device status via service
    device_service = DeviceService()
    await device_service.update_device_status(
        db=db,
        agent_id=agent_id,
        status=status,
        metadata=state.metadata
    )

    # Return acknowledgment
    return StateReportResponse(ack=True)


@router.get("/poll")
async def poll(
    agent_id: UUID = Query(..., description="Agent UUID"),
    authenticated_agent_id: UUID = Depends(get_agent_id_from_jwt),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Long-poll endpoint for agents to receive commands.

    Holds connection for up to poll_timeout_seconds, returning immediately
    if a pending command is available.

    Args:
        agent_id: Agent UUID from query parameter
        authenticated_agent_id: Agent UUID from JWT token
        db: Database session

    Returns:
        {"action": "none"} on timeout, or
        {"action": <command_type>, "payload": <command_payload>} on command

    Raises:
        HTTPException: 403 if agent_id doesn't match JWT
    """
    # Validate agent_id matches JWT claim
    if agent_id != authenticated_agent_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agent ID does not match token"
        )

    # Get or create signaling service instance
    signaling_service = SignalingService()

    # Hold poll connection
    command = await signaling_service.hold_poll(
        db,
        agent_id,
        timeout=settings.poll_timeout_seconds
    )

    # Return command or timeout response
    if command is None:
        return {"action": "none"}

    return {
        "action": command.type,
        "payload": command.payload_json
    }
