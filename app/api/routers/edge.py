"""Edge router - Agent-facing endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_agent_id_from_jwt
from app.database import get_db
from app.middleware.rate_limit_dependency import check_edge_rate_limit
from app.schemas.edge import StateReportRequest, StateReportResponse
from app.services.device_service import DeviceService
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
async def poll():
    """Placeholder long-poll endpoint."""
    return {"message": "Poll endpoint - to be implemented"}
