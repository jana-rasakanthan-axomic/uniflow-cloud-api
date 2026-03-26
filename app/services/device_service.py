"""Device service for device linking and management."""

import hashlib
import hmac
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import (
    InvalidSetupCodeError,
    InvalidTokenError,
    RevokedTokenError,
    SetupCodeAlreadyUsedError,
    SetupCodeExpiredError,
)
from app.models.device import Device
from app.models.refresh_token import RefreshToken
from app.models.setup_code import SetupCode
from app.repositories.device_repository import DeviceRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.services.audit_service import AuditService
from app.services.jwt_service import JWTService
from app.shared.enums import DeviceStatus


@dataclass
class TokenPair:
    """Data class for access and refresh token pair."""
    agent_id: UUID
    access_token: str
    refresh_token: str


class DeviceService:
    """Service for device linking and token issuance.

    Orchestrates setup code validation, device creation, refresh token tracking,
    JWT generation, and audit logging for the device linking flow.
    """

    def __init__(self):
        self.jwt_service = JWTService()
        self.audit_service = AuditService()
        self.token_repository = RefreshTokenRepository()
        self.device_repository = DeviceRepository()

    async def link_device(
        self,
        db: AsyncSession,
        setup_code: str,
        machine_info: dict[str, Any]
    ) -> TokenPair:
        """Link a device using a setup code and return JWT token pair.

        Args:
            db: Database session
            setup_code: 8-character setup code
            machine_info: Dictionary with keys:
                - machine_name: Human-readable machine name
                - os: Operating system version
                - source_ip: Source IP address

        Returns:
            TokenPair with agent_id, access_token, and refresh_token

        Raises:
            InvalidSetupCodeError: Code not found
            SetupCodeExpiredError: Code has expired
            SetupCodeAlreadyUsedError: Code already used

        Note:
            This method manages the transaction. It will commit on success
            and rollback on failure.
        """
        try:
            # Step 1: Validate and mark setup code as used (atomically)
            code = await self._validate_and_mark_used(db, setup_code)

            # Step 2: Create device record
            device = await self._create_device(
                db=db,
                org_id=code.org_id,
                machine_name=machine_info["machine_name"],
                os=machine_info["os"]
            )

            # Step 3: Generate JWT token pair first
            chain_id = uuid4()
            token_pair = self._generate_tokens(
                agent_id=device.agent_id,
                org_id=device.org_id,
                chain_id=chain_id
            )

            # Step 4: Create refresh token record with hash of actual JWT
            await self._create_refresh_token(
                db=db,
                device=device,
                chain_id=chain_id,
                refresh_token=token_pair.refresh_token
            )

            # Step 5: Log successful device link (before final commit)
            await self._log_success(
                db=db,
                org_id=device.org_id,
                agent_id=device.agent_id,
                setup_code=setup_code,
                machine_info=machine_info
            )

            # Commit transaction (all operations succeeded)
            await db.commit()

            return token_pair

        except (InvalidSetupCodeError, SetupCodeExpiredError, SetupCodeAlreadyUsedError):
            # Rollback device/token creation
            await db.rollback()

            # Log failure in separate transaction
            await self._log_failure(
                db=db,
                setup_code=setup_code,
                machine_info=machine_info,
                failure_reason=self._get_failure_reason(setup_code)
            )
            await db.commit()  # Commit audit log even on failure
            raise

        except Exception:
            # Rollback on unexpected error
            await db.rollback()
            raise

    async def _validate_and_mark_used(
        self,
        db: AsyncSession,
        setup_code: str
    ) -> SetupCode:
        """Validate setup code and mark it as used atomically.

        Args:
            db: Database session
            setup_code: 8-character setup code

        Returns:
            SetupCode instance

        Raises:
            InvalidSetupCodeError: Code not found
            SetupCodeExpiredError: Code has expired
            SetupCodeAlreadyUsedError: Code already used
        """
        # Find code (with FOR UPDATE lock for atomicity)
        code = await self._find_setup_code(db, setup_code)

        if code is None:
            raise InvalidSetupCodeError("Setup code not found")

        # Check if expired
        if code.expires_at < datetime.now(UTC):
            raise SetupCodeExpiredError("Setup code has expired")

        # Check if already used
        if code.used_at is not None:
            raise SetupCodeAlreadyUsedError("Setup code already used")

        # Mark as used
        code.used_at = datetime.now(UTC)
        db.add(code)

        return code

    async def _find_setup_code(
        self,
        db: AsyncSession,
        setup_code: str
    ) -> SetupCode | None:
        """Find setup code with SELECT FOR UPDATE lock.

        Args:
            db: Database session
            setup_code: 8-character setup code

        Returns:
            SetupCode instance or None if not found
        """
        result = await db.execute(
            select(SetupCode)
            .where(SetupCode.code == setup_code)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def _create_device(
        self,
        db: AsyncSession,
        org_id: UUID,
        machine_name: str,
        os: str
    ) -> Device:
        """Create device record with generated agent_id.

        Args:
            db: Database session
            org_id: Organization UUID
            machine_name: Human-readable machine name
            os: Operating system version

        Returns:
            Device instance
        """
        # For MVP, we're creating a "contributor" device without a specific user_id
        # In a full implementation, this would link to a User record
        device = Device(
            id=uuid4(),
            org_id=org_id,
            user_id=org_id,  # Placeholder - use org_id for now
            agent_id=self._generate_agent_id(),
            machine_name=machine_name,
            os=os,
            status="ONLINE",
            last_seen_at=datetime.now(UTC),
            created_at=datetime.now(UTC)
        )

        db.add(device)
        return device

    async def _create_refresh_token(
        self,
        db: AsyncSession,
        device: Device,
        chain_id: UUID,
        refresh_token: str
    ) -> RefreshToken:
        """Create initial refresh token record.

        Args:
            db: Database session
            device: Device instance
            chain_id: Token chain UUID
            refresh_token: The actual JWT refresh token to hash

        Returns:
            RefreshToken instance
        """
        # Hash the actual JWT token with HMAC
        token_hash = self._hash_token(refresh_token)

        refresh_token_record = RefreshToken(
            id=uuid4(),
            user_id=device.user_id,
            device_id=device.id,
            token_hash=token_hash,
            chain_id=chain_id,
            sequence_num=1,
            revoked_at=None,
            expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days),
            created_at=datetime.now(UTC)
        )

        db.add(refresh_token_record)
        return refresh_token_record

    def _generate_tokens(
        self,
        agent_id: UUID,
        org_id: UUID,
        chain_id: UUID
    ) -> TokenPair:
        """Generate JWT access and refresh token pair.

        Args:
            agent_id: Device agent UUID
            org_id: Organization UUID
            chain_id: Token chain UUID

        Returns:
            TokenPair with both tokens
        """
        access_token = self.jwt_service.create_access_token(
            agent_id=agent_id,
            org_id=org_id
        )

        refresh_token = self.jwt_service.create_refresh_token(
            agent_id=agent_id,
            org_id=org_id,
            chain_id=chain_id,
            sequence_num=1
        )

        return TokenPair(
            agent_id=agent_id,
            access_token=access_token,
            refresh_token=refresh_token
        )

    async def _log_success(
        self,
        db: AsyncSession,
        org_id: UUID,
        agent_id: UUID,
        setup_code: str,
        machine_info: dict[str, Any]
    ) -> None:
        """Log successful device link event.

        Args:
            db: Database session
            org_id: Organization UUID
            agent_id: Device agent UUID
            setup_code: Setup code (will be redacted)
            machine_info: Machine information
        """
        await self.audit_service.log_event(
            db=db,
            org_id=org_id,
            event_type="DEVICE_LINKED",
            actor_id=agent_id,
            source_ip=machine_info["source_ip"],
            metadata={
                "machine_name": machine_info["machine_name"],
                "os": machine_info["os"],
                "setup_code": self._redact_setup_code(setup_code)
            }
        )

    async def _log_failure(
        self,
        db: AsyncSession,
        setup_code: str,
        machine_info: dict[str, Any],
        failure_reason: str
    ) -> None:
        """Log failed device link attempt.

        Args:
            db: Database session
            setup_code: Setup code (will be redacted)
            machine_info: Machine information
            failure_reason: Reason for failure
        """
        # Try to get org_id from setup code (if it exists)
        org_id = None
        try:
            code = await self._find_setup_code(db, setup_code)
            if code is not None:
                org_id = code.org_id
        except Exception:
            # Ignore errors when looking up setup code for audit log
            pass

        await self.audit_service.log_event(
            db=db,
            org_id=org_id,  # May be None if code doesn't exist
            event_type="LINK_CODE_FAILED",
            actor_id=None,
            source_ip=machine_info["source_ip"],
            metadata={
                "setup_code_partial": self._redact_setup_code(setup_code),
                "failure_reason": failure_reason,
                "machine_name": machine_info["machine_name"]
            }
        )

    def _generate_agent_id(self) -> UUID:
        """Generate a cryptographically random agent ID (UUID v4).

        Returns:
            UUID v4 instance
        """
        return uuid4()

    def _hash_token(self, token: str) -> str:
        """Hash a token using HMAC-SHA256.

        Args:
            token: Token string to hash

        Returns:
            Hex-encoded HMAC hash

        Note:
            Uses jwt_secret as the HMAC key for additional security.
            This prevents attackers from pre-computing rainbow tables.
        """
        return hmac.new(
            settings.jwt_secret.encode(),
            token.encode(),
            hashlib.sha256
        ).hexdigest()

    def _redact_setup_code(self, code: str) -> str:
        """Partially redact setup code for audit logs.

        Args:
            code: 8-character setup code

        Returns:
            Redacted code (e.g., "****1234")
        """
        if len(code) >= 4:
            return f"****{code[-4:]}"
        return "****"

    def _get_failure_reason(self, setup_code: str) -> str:
        """Determine failure reason for audit logging.

        Args:
            setup_code: Setup code that failed

        Returns:
            Failure reason string
        """
        # This is a simplified version - in production we'd track the specific error
        return "INVALID"

    async def refresh_tokens(
        self,
        db: AsyncSession,
        refresh_token: str,
        source_ip: str
    ) -> TokenPair:
        """Rotate refresh token and issue new access token.

        Args:
            db: Database session
            refresh_token: JWT refresh token string
            source_ip: Source IP address

        Returns:
            TokenPair with new access and refresh tokens

        Raises:
            InvalidTokenError: Token invalid, expired, or not found
            RevokedTokenError: Token already revoked (reuse detected)

        Notes:
            - On reuse detection, revokes entire chain and logs security event
            - Transaction ensures atomicity: old token revoked before new issued
        """
        # Step 1: Verify JWT signature and expiration
        try:
            claims = self.jwt_service.verify_token(refresh_token)
        except (jwt.ExpiredSignatureError, jwt.InvalidSignatureError, jwt.DecodeError):
            raise InvalidTokenError("Invalid or expired refresh token") from None

        # Step 2: Look up token in database by hash
        token_hash = self._hash_token(refresh_token)
        old_token = await self.token_repository.find_by_token_hash(db, token_hash)

        if old_token is None:
            raise InvalidTokenError("Token not found")

        # Step 3: Check if token has been revoked (reuse detection)
        if old_token.revoked_at is not None:
            # Reuse detected - revoke entire chain and log
            await self.token_repository.revoke_chain(db, old_token.chain_id)

            await self.audit_service.log_event(
                db=db,
                org_id=UUID(claims["org_id"]),
                event_type="REFRESH_REUSE_DETECTED",
                actor_id=UUID(claims["sub"]),
                source_ip=source_ip,
                metadata={
                    "chain_id": str(old_token.chain_id),
                    "sequence_num": old_token.sequence_num
                }
            )

            await db.commit()
            raise RevokedTokenError("Token has been revoked")

        # Step 4: Revoke old token atomically
        await self.token_repository.revoke(db, old_token.id)

        # Step 5: Generate new JWT tokens first
        agent_id = UUID(claims["sub"])
        org_id = UUID(claims["org_id"])

        access_token = self.jwt_service.create_access_token(
            agent_id=agent_id,
            org_id=org_id
        )

        new_refresh_token = self.jwt_service.create_refresh_token(
            agent_id=agent_id,
            org_id=org_id,
            chain_id=old_token.chain_id,
            sequence_num=old_token.sequence_num + 1
        )

        # Step 6: Hash the actual refresh token with HMAC
        token_hash = self._hash_token(new_refresh_token)

        # Step 7: Create refresh token record with actual hash
        new_refresh_token_record = RefreshToken(
            id=uuid4(),
            user_id=old_token.user_id,
            device_id=old_token.device_id,
            token_hash=token_hash,
            chain_id=old_token.chain_id,
            sequence_num=old_token.sequence_num + 1,
            revoked_at=None,
            expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days),
            created_at=datetime.now(UTC)
        )

        await self.token_repository.create(db, new_refresh_token_record)

        # Commit all changes (revoke old token + create new token)
        try:
            await db.commit()
        except Exception:
            await db.rollback()
            raise

        return TokenPair(
            agent_id=agent_id,
            access_token=access_token,
            refresh_token=new_refresh_token
        )

    async def update_device_status(
        self,
        db: AsyncSession,
        agent_id: UUID,
        status: DeviceStatus,
        metadata: dict | None = None
    ) -> Device:
        """Update device status and last_seen_at timestamp.

        Args:
            db: Database session
            agent_id: Device agent UUID
            status: New device status (ONLINE/OFFLINE)
            metadata: Optional metadata dictionary (agent_version, disk_space, etc.)

        Returns:
            Updated Device instance

        Note:
            When marking device OFFLINE, the repository preserves the original
            last_seen_at timestamp. When marking ONLINE, it updates to current time.
        """
        # Update device status via repository
        updated_device = await self.device_repository.update_status(
            db=db,
            agent_id=agent_id,
            status=status,
            metadata=metadata
        )

        return updated_device
