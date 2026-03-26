"""Pydantic schemas for request/response validation."""

from app.schemas.auth import DeviceLinkRequest, DeviceLinkResponse

__all__ = [
    "DeviceLinkRequest",
    "DeviceLinkResponse",
]
