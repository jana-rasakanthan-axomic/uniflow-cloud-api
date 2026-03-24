"""Web router - Portal-facing endpoints."""

from fastapi import APIRouter, Depends

from app.middleware.rate_limit_dependency import check_web_rate_limit

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
