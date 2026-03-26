"""FastAPI dependencies for rate limiting."""

from fastapi import HTTPException, Request
from starlette.responses import Response

from app.config import settings
from app.middleware.rate_limit_keys import get_agent_key, get_ip_key, get_user_key
from app.middleware.rate_limiter import RateLimiter

# Create rate limiter instances for each router
auth_limiter = RateLimiter(
    requests=settings.auth_rate_limit,
    window_seconds=settings.rate_limit_window,
    key_func=get_ip_key,
)

web_limiter = RateLimiter(
    requests=settings.web_rate_limit,
    window_seconds=settings.rate_limit_window,
    key_func=get_user_key,
)

edge_limiter = RateLimiter(
    requests=settings.edge_rate_limit,
    window_seconds=settings.rate_limit_window,
    key_func=get_agent_key,
)

# Stricter rate limiter for device link endpoint (setup code attempts)
device_link_limiter = RateLimiter(
    requests=5,  # 5 attempts
    window_seconds=300,  # per 5 minutes
    key_func=get_ip_key,
)


async def check_auth_rate_limit(request: Request, response: Response):
    """
    Dependency to check auth router rate limit.

    Raises:
        HTTPException: 429 if rate limit exceeded
    """
    key = get_ip_key(request)
    allowed, retry_after = await auth_limiter.check_limit(key)

    if not allowed:
        response.headers["Retry-After"] = str(retry_after)
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )


async def check_web_rate_limit(request: Request, response: Response):
    """
    Dependency to check web router rate limit.

    Raises:
        HTTPException: 429 if rate limit exceeded
    """
    key = get_user_key(request)
    allowed, retry_after = await web_limiter.check_limit(key)

    if not allowed:
        response.headers["Retry-After"] = str(retry_after)
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )


async def check_edge_rate_limit(request: Request, response: Response):
    """
    Dependency to check edge router rate limit.

    Raises:
        HTTPException: 429 if rate limit exceeded
    """
    key = get_agent_key(request)
    allowed, retry_after = await edge_limiter.check_limit(key)

    if not allowed:
        response.headers["Retry-After"] = str(retry_after)
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )


async def check_device_link_rate_limit(request: Request, response: Response):
    """
    Dependency to check device link endpoint rate limit (stricter).

    Raises:
        HTTPException: 429 if rate limit exceeded
    """
    key = get_ip_key(request)
    allowed, retry_after = await device_link_limiter.check_limit(key)

    if not allowed:
        response.headers["Retry-After"] = str(retry_after)
        raise HTTPException(
            status_code=429,
            detail="Too many device link attempts. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )
