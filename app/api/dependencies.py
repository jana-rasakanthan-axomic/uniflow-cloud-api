"""FastAPI dependencies for authentication and authorization."""

from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from app.services.signaling_service import SignalingService

# HTTP Bearer security scheme
security = HTTPBearer()


async def get_agent_id_from_jwt(
    credentials: HTTPAuthorizationCredentials = Depends(security)  # noqa: B008
) -> UUID:
    """Extract and validate agent_id from JWT token.

    Args:
        credentials: HTTP Bearer credentials from Authorization header

    Returns:
        Agent UUID extracted from token claims

    Raises:
        HTTPException: 401 if token is invalid, expired, or malformed
    """
    try:
        # Decode and verify JWT token
        token = credentials.credentials
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )

        # Extract agent_id from 'sub' claim
        agent_id_str = payload.get("sub")
        if not agent_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject claim"
            )

        # Convert to UUID
        agent_id = UUID(agent_id_str)

        return agent_id

    except jwt.ExpiredSignatureError:
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidSignatureError:
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token signature"
        )
    except jwt.DecodeError:
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format"
        )
    except ValueError:
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid agent ID format"
        )


def get_signaling_service(request: Request) -> SignalingService:
    """Get singleton SignalingService from app state.

    Args:
        request: FastAPI request object

    Returns:
        SignalingService singleton instance
    """
    return request.app.state.signaling_service
