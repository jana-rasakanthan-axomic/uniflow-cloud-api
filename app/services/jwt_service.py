"""JWT service for token generation and validation."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from app.config import settings


class JWTService:
    """Service for creating and verifying JWT tokens.

    Handles both access tokens (1-hour expiry) and refresh tokens (90-day expiry)
    with device-scoped claims for edge agent authentication.
    """

    def create_access_token(self, agent_id: UUID, org_id: UUID) -> str:
        """Create a short-lived access token for API authentication.

        Args:
            agent_id: Device agent UUID (subject of the token)
            org_id: Organization UUID

        Returns:
            Signed JWT token string

        Claims:
            - sub: agent_id (device identifier)
            - org_id: organization UUID
            - type: "access"
            - iat: issued at timestamp
            - exp: expiration timestamp (1 hour from now)
        """
        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=settings.access_token_expire_minutes)

        claims = {
            "sub": str(agent_id),
            "org_id": str(org_id),
            "type": "access",
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
        }

        return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    def create_refresh_token(
        self,
        agent_id: UUID,
        org_id: UUID,
        chain_id: UUID,
        sequence_num: int
    ) -> str:
        """Create a long-lived refresh token for token rotation.

        Args:
            agent_id: Device agent UUID (subject of the token)
            org_id: Organization UUID
            chain_id: Token chain UUID (for tracking token families)
            sequence_num: Sequence number in the token chain (starts at 1)

        Returns:
            Signed JWT token string

        Claims:
            - sub: agent_id (device identifier)
            - org_id: organization UUID
            - chain_id: token chain UUID
            - sequence_num: sequence number in chain
            - type: "refresh"
            - iat: issued at timestamp
            - exp: expiration timestamp (90 days from now)
        """
        now = datetime.now(UTC)
        expires_at = now + timedelta(days=settings.refresh_token_expire_days)

        claims = {
            "sub": str(agent_id),
            "org_id": str(org_id),
            "chain_id": str(chain_id),
            "sequence_num": sequence_num,
            "type": "refresh",
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
        }

        return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    def verify_token(self, token: str) -> dict:
        """Verify and decode a JWT token.

        Args:
            token: JWT token string to verify

        Returns:
            Dictionary of decoded claims

        Raises:
            jwt.ExpiredSignatureError: Token has expired
            jwt.InvalidSignatureError: Token signature is invalid
            jwt.DecodeError: Token is malformed
        """
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )
