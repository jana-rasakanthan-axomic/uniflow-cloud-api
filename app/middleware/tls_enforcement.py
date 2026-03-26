"""TLS enforcement middleware for FastAPI.

This middleware ensures all requests are made over HTTPS (TLS 1.2+).
It checks the X-Forwarded-Proto header set by the AWS Application Load Balancer.

Non-HTTPS requests receive a 403 Forbidden response.
"""

from fastapi import Request, Response
from fastapi.responses import JSONResponse


async def enforce_tls(request: Request, call_next) -> Response:
    """Enforce TLS/HTTPS for all requests.

    Args:
        request: The incoming request
        call_next: The next middleware or route handler

    Returns:
        Response object (either 403 error or forwarded response)

    Raises:
        None - returns 403 JSONResponse on TLS violation
    """
    # Get the X-Forwarded-Proto header (set by ALB)
    forwarded_proto = request.headers.get("x-forwarded-proto", "").lower()

    # Check if request is HTTPS
    # Note: In local development, you might want to bypass this check
    # For now, we enforce HTTPS in all environments
    if forwarded_proto != "https":
        return JSONResponse(
            status_code=403,
            content={
                "detail": "HTTPS required. All requests must use TLS 1.2 or higher.",
                "error": "insecure_connection",
            },
        )

    # Request is secure, proceed
    response = await call_next(request)
    return response
