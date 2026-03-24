"""Rate limit key extraction functions for different router types."""

from fastapi import Request


def get_ip_key(request: Request) -> str:
    """
    Extract IP address for auth router rate limiting.

    Args:
        request: FastAPI Request object

    Returns:
        Client IP address as string
    """
    # Check for X-Forwarded-For header (proxy/load balancer)
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # Take first IP in chain (original client)
        return forwarded_for.split(",")[0].strip()

    # Fall back to direct client IP
    if request.client:
        return request.client.host

    # Fallback for testing
    return "unknown"


def get_user_key(request: Request) -> str:
    """
    Extract user_id from JWT for web router rate limiting.

    Placeholder implementation: reads from X-User-ID header.
    In production, this will decode the JWT and extract the sub claim.

    Args:
        request: FastAPI Request object

    Returns:
        User ID as string
    """
    # Placeholder: read from header (will be replaced with JWT decode)
    user_id = request.headers.get("x-user-id", "anonymous")
    return f"user:{user_id}"


def get_agent_key(request: Request) -> str:
    """
    Extract agent_id from JWT for edge router rate limiting.

    Placeholder implementation: reads from X-Agent-ID header.
    In production, this will decode the JWT and extract the sub claim.

    Args:
        request: FastAPI Request object

    Returns:
        Agent ID as string
    """
    # Placeholder: read from header (will be replaced with JWT decode)
    agent_id = request.headers.get("x-agent-id", "anonymous")
    return f"agent:{agent_id}"
