"""Edge router - Agent-facing endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_agent_id_from_jwt, get_signaling_service
from app.config import settings
from app.database import get_db
from app.middleware.rate_limit_dependency import check_edge_rate_limit
from app.repositories.file_repository import FileRepository
from app.repositories.job_repository import JobRepository
from app.schemas.edge import StateReportRequest, StateReportResponse
from app.schemas.upload import ProgressRequest, ProgressResponse, STSRequest, STSResponse
from app.services.device_service import DeviceService
from app.services.signaling_service import SignalingService
from app.services.sts_service import STSService
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
    db: AsyncSession = Depends(get_db),
    signaling_service: SignalingService = Depends(get_signaling_service)
) -> dict:
    """Long-poll endpoint for agents to receive commands.

    Holds connection for up to poll_timeout_seconds, returning immediately
    if a pending command is available.

    Args:
        agent_id: Agent UUID from query parameter
        authenticated_agent_id: Agent UUID from JWT token
        db: Database session
        signaling_service: Singleton SignalingService

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

    # Hold poll connection
    command = await signaling_service.hold_poll(
        db,
        agent_id,
        timeout=settings.poll_timeout_seconds
    )

    # Return command or timeout response
    if command is None:
        return {"action": "none"}

    # Commit the command status update (from PENDING to DELIVERED)
    await db.commit()

    return {
        "action": command.type,
        "payload": command.payload_json,
        "command_id": str(command.id)
    }


@router.post("/upload/sts", response_model=STSResponse)
async def issue_sts_credentials(
    request: STSRequest,
    agent_id: UUID = Depends(get_agent_id_from_jwt),
    db: AsyncSession = Depends(get_db)
) -> STSResponse:
    """Issue scoped STS credentials for direct S3 upload.

    Args:
        request: STS request with job_id and file_ids
        agent_id: Agent UUID from JWT
        db: Database session

    Returns:
        STS credentials and upload targets

    Raises:
        HTTPException 400: Invalid job_id or file_ids
        HTTPException 403: Agent does not own the requested files
        HTTPException 404: Job not found or files not in PRE_REGISTERED state
        HTTPException 500: AWS STS call failed
    """
    # Verify job exists
    job_repo = JobRepository()
    job = await job_repo.find_by_id(db, request.job_id)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # Verify agent owns all requested files
    file_repo = FileRepository()
    owns_files = await file_repo.verify_agent_ownership(db, agent_id, request.file_ids)

    if not owns_files:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agent does not own all requested files"
        )

    # Get org_id from job
    org_id = job.org_id

    # Build file targets with actual file metadata
    file_targets = []
    job_files = await file_repo.find_by_job_id(db, request.job_id)

    # Create a map of file_id to job_file for quick lookup
    file_map = {jf.id: jf for jf in job_files}

    for file_id in request.file_ids:
        job_file = file_map.get(file_id)
        if job_file is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File {file_id} not found in job"
            )

        # Verify file is in PRE_REGISTERED state
        if job_file.status != "PRE_REGISTERED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File {file_id} is not in PRE_REGISTERED state"
            )

        file_targets.append({
            "file_id": file_id,
            "oa_asset_id": job_file.oa_asset_id or f"oa_{file_id.hex[:8]}",
            "filename": f"file_{file_id.hex[:8]}.jpg"  # TODO: Get from asset metadata
        })

    # Issue STS credentials
    sts_service = STSService()
    result = await sts_service.issue_sts_credentials(
        agent_id=agent_id,
        org_id=org_id,
        job_id=request.job_id,
        file_targets=file_targets
    )

    return STSResponse(
        credentials=result["credentials"],
        upload_targets=result["upload_targets"]
    )


@router.post("/upload/progress", response_model=ProgressResponse)
async def report_progress(
    request: ProgressRequest,
    agent_id: UUID = Depends(get_agent_id_from_jwt),
    db: AsyncSession = Depends(get_db)
) -> ProgressResponse:
    """Report chunk-level upload progress.

    Args:
        request: Progress request with file_id, chunks, status
        agent_id: Agent UUID from JWT
        db: Database session

    Returns:
        Progress acknowledgment

    Raises:
        HTTPException 400: Invalid payload or illegal status transition
        HTTPException 401: Agent not authenticated
        HTTPException 404: Job or file not found
        HTTPException 500: Database update failed
    """
    # Update file status and progress
    file_repo = FileRepository()

    try:
        updated_file = await file_repo.update_file_status(
            db=db,
            file_id=request.file_id,
            status=request.status,
            chunks_completed=request.chunks_completed,
            total_chunks=request.total_chunks,
            streaming_hash=request.streaming_hash,
            error_message=request.error_message
        )

        await db.commit()

        return ProgressResponse(
            ack=True,
            file_status=updated_file.status
        )

    except ValueError as e:
        # Invalid status transition
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        ) from e
    except Exception as e:
        # Database update failed
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update file progress"
        ) from e
