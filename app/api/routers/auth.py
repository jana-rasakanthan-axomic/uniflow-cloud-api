"""Auth router - OAuth/PKCE, JWT tokens, device linking."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import (
    InvalidSetupCodeError,
    InvalidTokenError,
    RevokedTokenError,
    SetupCodeAlreadyUsedError,
    SetupCodeExpiredError,
)
from app.middleware.rate_limit_dependency import check_auth_rate_limit
from app.schemas.auth import (
    DeviceLinkRequest,
    DeviceLinkResponse,
    TokenRefreshRequest,
    TokenRefreshResponse,
)
from app.services.device_service import DeviceService

router = APIRouter(dependencies=[Depends(check_auth_rate_limit)])


@router.post("/login")
async def login():
    """Placeholder login endpoint."""
    return {"message": "Login endpoint - to be implemented"}


@router.post("/token")
async def token():
    """Placeholder token endpoint."""
    return {"message": "Token endpoint - to be implemented"}


@router.post("/device/link", response_model=DeviceLinkResponse)
async def device_link(
    request: Request,
    link_request: DeviceLinkRequest,
    db: AsyncSession = Depends(get_db)
):
    """Link a device using a setup code.

    Validates the setup code, creates a device record, and returns
    JWT access and refresh tokens for API authentication.

    Args:
        request: FastAPI request object (for extracting source IP)
        link_request: Device link request with setup_code, machine_name, os
        db: Database session dependency

    Returns:
        DeviceLinkResponse with agent_id and token pair

    Raises:
        HTTPException 401: Invalid or expired setup code
        HTTPException 410: Setup code already used
        HTTPException 422: Validation error (malformed request)
    """
    # Extract source IP from X-Forwarded-For header (behind ALB) or request.client
    source_ip = _extract_source_ip(request)

    # Prepare machine info for service
    machine_info = {
        "machine_name": link_request.machine_name,
        "os": link_request.os,
        "source_ip": source_ip
    }

    # Call device service
    device_service = DeviceService()

    try:
        token_pair = await device_service.link_device(
            db=db,
            setup_code=link_request.setup_code,
            machine_info=machine_info
        )

        return DeviceLinkResponse(
            agent_id=token_pair.agent_id,
            access_token=token_pair.access_token,
            refresh_token=token_pair.refresh_token
        )

    except SetupCodeAlreadyUsedError:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Setup code already used"
        ) from None

    except (InvalidSetupCodeError, SetupCodeExpiredError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired setup code"
        ) from None


@router.post("/tokens/refresh", response_model=TokenRefreshResponse)
async def refresh_token(
    request: Request,
    refresh_request: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db)
):
    """Refresh an access token using a refresh token.

    Validates the refresh token, issues a new access token and rotated refresh token.
    Automatically revokes the old refresh token to prevent reuse.

    Args:
        request: FastAPI request object (for extracting source IP)
        refresh_request: Token refresh request with refresh_token
        db: Database session dependency

    Returns:
        TokenRefreshResponse with new access_token and refresh_token

    Raises:
        HTTPException 401: Invalid or expired refresh token
        HTTPException 403: Revoked token (reuse detected)
        HTTPException 422: Validation error (malformed request)
    """
    # Extract source IP from X-Forwarded-For header (behind ALB) or request.client
    source_ip = _extract_source_ip(request)

    # Call device service
    device_service = DeviceService()

    try:
        token_pair = await device_service.refresh_tokens(
            db=db,
            refresh_token=refresh_request.refresh_token,
            source_ip=source_ip
        )

        return TokenRefreshResponse(
            access_token=token_pair.access_token,
            refresh_token=token_pair.refresh_token
        )

    except RevokedTokenError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or revoked token"
        ) from None

    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        ) from None


def _extract_source_ip(request: Request) -> str:
    """Extract source IP address from request.

    Args:
        request: FastAPI request object

    Returns:
        Source IP address (IPv4 or IPv6)

    Note:
        When deployed behind AWS ALB, X-Forwarded-For header contains
        the original client IP as the first entry in a comma-separated list.
        Falls back to request.client.host in development environments.
    """
    x_forwarded_for = request.headers.get("X-Forwarded-For")

    if x_forwarded_for:
        # Take first IP from comma-separated list (original client)
        return x_forwarded_for.split(",")[0].strip()

    # Fallback to direct client IP (dev environment)
    if request.client:
        return request.client.host

    return "unknown"
