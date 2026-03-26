"""Auth request/response schemas."""

import re
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class DeviceLinkRequest(BaseModel):
    """Request schema for POST /auth/device/link endpoint.

    Validates setup code format and device information for edge agent linking.
    """

    setup_code: str = Field(
        ...,
        min_length=8,
        max_length=8,
        description="8-character alphanumeric uppercase setup code"
    )
    machine_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Human-readable machine name"
    )
    os: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Operating system version (e.g., 'Windows 11', 'macOS 14.2')"
    )

    @field_validator("setup_code")
    @classmethod
    def validate_setup_code_format(cls, v: str) -> str:
        """Validate setup code is exactly 8 alphanumeric uppercase characters."""
        if not re.match(r"^[A-Z0-9]{8}$", v):
            raise ValueError(
                "setup_code must be exactly 8 alphanumeric uppercase characters"
            )
        return v


class DeviceLinkResponse(BaseModel):
    """Response schema for successful device linking.

    Returns the device's agent_id and JWT token pair for authentication.
    """

    agent_id: UUID = Field(
        ...,
        description="Unique device identifier (UUID v4)"
    )
    access_token: str = Field(
        ...,
        min_length=1,
        description="JWT access token (1-hour expiry)"
    )
    refresh_token: str = Field(
        ...,
        min_length=1,
        description="JWT refresh token (90-day expiry)"
    )


class TokenRefreshRequest(BaseModel):
    """Request schema for POST /auth/tokens/refresh endpoint.

    Validates refresh token for token rotation.
    """

    refresh_token: str = Field(
        ...,
        min_length=1,
        description="JWT refresh token to rotate"
    )


class TokenRefreshResponse(BaseModel):
    """Response schema for successful token refresh.

    Returns a new access token and rotated refresh token.
    """

    access_token: str = Field(
        ...,
        min_length=1,
        description="New JWT access token (1-hour expiry)"
    )
    refresh_token: str = Field(
        ...,
        min_length=1,
        description="New JWT refresh token (90-day expiry, incremented sequence)"
    )
