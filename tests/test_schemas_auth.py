"""Tests for auth request/response schemas."""

from uuid import UUID

import pytest
from pydantic import ValidationError

from app.schemas.auth import DeviceLinkRequest, DeviceLinkResponse


class TestDeviceLinkRequest:
    """Test DeviceLinkRequest schema validation."""

    def test_valid_request(self):
        """Test valid device link request with all fields."""
        request = DeviceLinkRequest(
            setup_code="ABCD1234",
            machine_name="John's MacBook Pro",
            os="macOS 14.2"
        )
        assert request.setup_code == "ABCD1234"
        assert request.machine_name == "John's MacBook Pro"
        assert request.os == "macOS 14.2"

    def test_setup_code_must_be_8_chars(self):
        """Test setup code must be exactly 8 characters."""
        with pytest.raises(ValidationError) as exc_info:
            DeviceLinkRequest(
                setup_code="ABC123",  # Too short
                machine_name="Test Machine",
                os="Windows 11"
            )
        assert "setup_code" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            DeviceLinkRequest(
                setup_code="ABCD12345",  # Too long
                machine_name="Test Machine",
                os="Windows 11"
            )
        assert "setup_code" in str(exc_info.value)

    def test_setup_code_must_be_alphanumeric_uppercase(self):
        """Test setup code must be alphanumeric uppercase only."""
        with pytest.raises(ValidationError) as exc_info:
            DeviceLinkRequest(
                setup_code="abcd1234",  # Lowercase
                machine_name="Test Machine",
                os="Windows 11"
            )
        assert "setup_code" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            DeviceLinkRequest(
                setup_code="ABCD-234",  # Contains hyphen
                machine_name="Test Machine",
                os="Windows 11"
            )
        assert "setup_code" in str(exc_info.value)

    def test_machine_name_required(self):
        """Test machine_name is required."""
        with pytest.raises(ValidationError) as exc_info:
            DeviceLinkRequest(
                setup_code="ABCD1234",
                machine_name="",
                os="Windows 11"
            )
        assert "machine_name" in str(exc_info.value)

    def test_machine_name_max_length(self):
        """Test machine_name max length is 255 characters."""
        long_name = "A" * 256
        with pytest.raises(ValidationError) as exc_info:
            DeviceLinkRequest(
                setup_code="ABCD1234",
                machine_name=long_name,
                os="Windows 11"
            )
        assert "machine_name" in str(exc_info.value)

        # Should work with 255 chars
        valid_name = "A" * 255
        request = DeviceLinkRequest(
            setup_code="ABCD1234",
            machine_name=valid_name,
            os="Windows 11"
        )
        assert len(request.machine_name) == 255

    def test_os_required(self):
        """Test os is required."""
        with pytest.raises(ValidationError) as exc_info:
            DeviceLinkRequest(
                setup_code="ABCD1234",
                machine_name="Test Machine",
                os=""
            )
        assert "os" in str(exc_info.value)

    def test_os_max_length(self):
        """Test os max length is 100 characters."""
        long_os = "A" * 101
        with pytest.raises(ValidationError) as exc_info:
            DeviceLinkRequest(
                setup_code="ABCD1234",
                machine_name="Test Machine",
                os=long_os
            )
        assert "os" in str(exc_info.value)

        # Should work with 100 chars
        valid_os = "A" * 100
        request = DeviceLinkRequest(
            setup_code="ABCD1234",
            machine_name="Test Machine",
            os=valid_os
        )
        assert len(request.os) == 100


class TestDeviceLinkResponse:
    """Test DeviceLinkResponse schema."""

    def test_valid_response(self):
        """Test valid device link response with all fields."""
        agent_id = UUID("12345678-1234-5678-1234-567812345678")
        response = DeviceLinkResponse(
            agent_id=agent_id,
            access_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            refresh_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        )
        assert response.agent_id == agent_id
        assert response.access_token == "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        assert response.refresh_token == "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

    def test_agent_id_must_be_uuid(self):
        """Test agent_id must be a valid UUID."""
        with pytest.raises(ValidationError) as exc_info:
            DeviceLinkResponse(
                agent_id="not-a-uuid",
                access_token="token1",
                refresh_token="token2"
            )
        assert "agent_id" in str(exc_info.value)

    def test_tokens_required(self):
        """Test access_token and refresh_token are required."""
        agent_id = UUID("12345678-1234-5678-1234-567812345678")

        with pytest.raises(ValidationError):
            DeviceLinkResponse(
                agent_id=agent_id,
                access_token="",
                refresh_token="token"
            )

        with pytest.raises(ValidationError):
            DeviceLinkResponse(
                agent_id=agent_id,
                access_token="token",
                refresh_token=""
            )
