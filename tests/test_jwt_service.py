"""Tests for JWT service."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from app.config import settings
from app.services.jwt_service import JWTService


class TestJWTService:
    """Test JWT token generation and validation."""

    @pytest.fixture
    def jwt_service(self):
        """Create JWT service instance."""
        return JWTService()

    @pytest.fixture
    def test_agent_id(self):
        """Test agent UUID."""
        return uuid4()

    @pytest.fixture
    def test_org_id(self):
        """Test organization UUID."""
        return uuid4()

    @pytest.fixture
    def test_chain_id(self):
        """Test refresh token chain UUID."""
        return uuid4()

    def test_create_access_token(self, jwt_service, test_agent_id, test_org_id):
        """Test access token generation with correct claims."""
        token = jwt_service.create_access_token(
            agent_id=test_agent_id,
            org_id=test_org_id
        )

        # Token should be a non-empty string
        assert isinstance(token, str)
        assert len(token) > 0

        # Decode and verify claims
        decoded = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )

        assert decoded["sub"] == str(test_agent_id)
        assert decoded["org_id"] == str(test_org_id)
        assert decoded["type"] == "access"
        assert "exp" in decoded
        assert "iat" in decoded

    def test_create_access_token_expiry(self, jwt_service, test_agent_id, test_org_id):
        """Test access token has 1-hour expiry."""
        token = jwt_service.create_access_token(
            agent_id=test_agent_id,
            org_id=test_org_id
        )

        decoded = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )

        exp_time = datetime.fromtimestamp(decoded["exp"], tz=UTC)
        iat_time = datetime.fromtimestamp(decoded["iat"], tz=UTC)

        # Should expire in approximately 1 hour (60 minutes)
        expiry_duration = exp_time - iat_time
        assert 59 * 60 <= expiry_duration.total_seconds() <= 61 * 60

    def test_create_refresh_token(
        self, jwt_service, test_agent_id, test_org_id, test_chain_id
    ):
        """Test refresh token generation with correct claims."""
        token = jwt_service.create_refresh_token(
            agent_id=test_agent_id,
            org_id=test_org_id,
            chain_id=test_chain_id,
            sequence_num=1
        )

        # Token should be a non-empty string
        assert isinstance(token, str)
        assert len(token) > 0

        # Decode and verify claims
        decoded = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )

        assert decoded["sub"] == str(test_agent_id)
        assert decoded["org_id"] == str(test_org_id)
        assert decoded["chain_id"] == str(test_chain_id)
        assert decoded["sequence_num"] == 1
        assert decoded["type"] == "refresh"
        assert "exp" in decoded
        assert "iat" in decoded

    def test_create_refresh_token_expiry(
        self, jwt_service, test_agent_id, test_org_id, test_chain_id
    ):
        """Test refresh token has 90-day expiry."""
        token = jwt_service.create_refresh_token(
            agent_id=test_agent_id,
            org_id=test_org_id,
            chain_id=test_chain_id,
            sequence_num=1
        )

        decoded = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )

        exp_time = datetime.fromtimestamp(decoded["exp"], tz=UTC)
        iat_time = datetime.fromtimestamp(decoded["iat"], tz=UTC)

        # Should expire in approximately 90 days
        expiry_duration = exp_time - iat_time
        assert 89.5 <= expiry_duration.total_seconds() / (24 * 60 * 60) <= 90.5

    def test_verify_token_valid(self, jwt_service, test_agent_id, test_org_id):
        """Test verifying a valid access token."""
        token = jwt_service.create_access_token(
            agent_id=test_agent_id,
            org_id=test_org_id
        )

        claims = jwt_service.verify_token(token)

        assert claims["sub"] == str(test_agent_id)
        assert claims["org_id"] == str(test_org_id)
        assert claims["type"] == "access"

    def test_verify_token_expired(self, jwt_service, test_agent_id, test_org_id):
        """Test verifying an expired token raises error."""
        # Create a token that's already expired
        past_time = datetime.now(UTC) - timedelta(hours=2)
        claims = {
            "sub": str(test_agent_id),
            "org_id": str(test_org_id),
            "type": "access",
            "iat": int(past_time.timestamp()),
            "exp": int((past_time + timedelta(minutes=1)).timestamp())
        }
        expired_token = jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)

        with pytest.raises(jwt.ExpiredSignatureError):
            jwt_service.verify_token(expired_token)

    def test_verify_token_invalid_signature(self, jwt_service):
        """Test verifying a token with invalid signature raises error."""
        # Create a token with a different secret
        claims = {
            "sub": str(uuid4()),
            "org_id": str(uuid4()),
            "type": "access",
            "iat": int(datetime.now(UTC).timestamp()),
            "exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp())
        }
        invalid_token = jwt.encode(claims, "wrong-secret", algorithm="HS256")

        with pytest.raises(jwt.InvalidSignatureError):
            jwt_service.verify_token(invalid_token)

    def test_verify_token_malformed(self, jwt_service):
        """Test verifying a malformed token raises error."""
        with pytest.raises(jwt.DecodeError):
            jwt_service.verify_token("not.a.valid.jwt.token")

    def test_refresh_token_sequence_numbers(
        self, jwt_service, test_agent_id, test_org_id, test_chain_id
    ):
        """Test refresh tokens can have different sequence numbers."""
        token1 = jwt_service.create_refresh_token(
            agent_id=test_agent_id,
            org_id=test_org_id,
            chain_id=test_chain_id,
            sequence_num=1
        )

        token2 = jwt_service.create_refresh_token(
            agent_id=test_agent_id,
            org_id=test_org_id,
            chain_id=test_chain_id,
            sequence_num=2
        )

        decoded1 = jwt.decode(token1, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        decoded2 = jwt.decode(token2, settings.jwt_secret, algorithms=[settings.jwt_algorithm])

        assert decoded1["sequence_num"] == 1
        assert decoded2["sequence_num"] == 2
        assert decoded1["chain_id"] == decoded2["chain_id"]
