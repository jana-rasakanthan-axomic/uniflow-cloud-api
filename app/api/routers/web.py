"""Web router - Portal-facing endpoints."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions.job_exceptions import InvalidTransitionError
from app.middleware.rate_limit_dependency import check_web_rate_limit
from app.schemas.job_schemas import (
    ConflictErrorResponse,
    JobStateTransitionRequest,
    JobStateTransitionResponse,
)
from app.services.job_service import JobService
from app.shared.enums.job_status import JobStatus

router = APIRouter(dependencies=[Depends(check_web_rate_limit)])


@router.get("/dashboard")
async def dashboard():
    """Placeholder dashboard endpoint."""
    return {"message": "Dashboard endpoint - to be implemented"}


@router.get("/jobs")
async def list_jobs():
    """Placeholder jobs list endpoint."""
    return {"message": "Jobs endpoint - to be implemented"}


@router.get("/devices")
async def list_devices():
    """Placeholder devices list endpoint."""
    return {"message": "Devices endpoint - to be implemented"}


@router.patch(
    "/jobs/{job_id}/state",
    response_model=JobStateTransitionResponse,
    status_code=status.HTTP_200_OK,
    responses={
        409: {"model": ConflictErrorResponse, "description": "Invalid state transition"},
        404: {"description": "Job not found"},
    },
)
async def transition_job_state(
    job_id: UUID,
    request: JobStateTransitionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Transition a job to a new state.

    Validates the state transition using the state machine and updates
    the job status in the database.

    Args:
        job_id: UUID of the job to transition
        request: Request containing the action to perform
        db: Database session

    Returns:
        JobStateTransitionResponse with updated job information

    Raises:
        HTTPException 404: Job not found
        HTTPException 409: Invalid state transition
    """
    job_service = JobService()

    try:
        updated_job = await job_service.transition_state(db, job_id, request.action)

        return JobStateTransitionResponse(
            job_id=updated_job.id,
            status=JobStatus(updated_job.status),
            transitioned_at=datetime.now(UTC),
        )

    except ValueError as e:
        # Job not found
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        ) from e

    except InvalidTransitionError as e:
        # Invalid state transition
        conflict_response = ConflictErrorResponse(
            detail=e.detail,
            current_state=JobStatus(e.current_state),
            attempted_action=e.action,
        )
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=conflict_response.model_dump(),
        )
