"""Tests for PII scrubbing log filter."""

import pytest

from app.utils.pii_scrubber import scrub_pii


def test_pii_scrubber_removes_email():
    """Test that PII scrubber strips email addresses."""
    message = "User john.doe@example.com uploaded file"
    result = scrub_pii(message)

    assert "john.doe@example.com" not in result
    assert "[REDACTED]" in result
    assert "User" in result
    assert "uploaded file" in result


def test_pii_scrubber_removes_multiple_emails():
    """Test that PII scrubber strips multiple email addresses."""
    message = "Contact alice@example.com or bob@test.org for help"
    result = scrub_pii(message)

    assert "alice@example.com" not in result
    assert "bob@test.org" not in result
    assert "[REDACTED]" in result
    assert "Contact" in result


def test_pii_scrubber_removes_windows_file_path():
    """Test that PII scrubber strips Windows file paths."""
    message = "File located at C:\\Users\\John\\Documents\\file.pdf"
    result = scrub_pii(message)

    assert "C:\\Users\\John\\Documents\\file.pdf" not in result
    assert "[REDACTED]" in result
    assert "File located at" in result


def test_pii_scrubber_removes_unix_file_path():
    """Test that PII scrubber strips Unix file paths."""
    message = "Processing /home/john/projects/secret/data.csv"
    result = scrub_pii(message)

    assert "/home/john/projects/secret/data.csv" not in result
    assert "[REDACTED]" in result
    assert "Processing" in result


def test_pii_scrubber_removes_password():
    """Test that PII scrubber strips password field."""
    message = "Auth failed: password=secret123"
    result = scrub_pii(message)

    assert "secret123" not in result
    assert "[REDACTED]" in result
    assert "Auth failed:" in result


def test_pii_scrubber_removes_token():
    """Test that PII scrubber strips token field."""
    message = "Request failed: token=abc123xyz"
    result = scrub_pii(message)

    assert "abc123xyz" not in result
    assert "[REDACTED]" in result


def test_pii_scrubber_removes_api_key():
    """Test that PII scrubber strips API key field."""
    message = "Config: api_key: sk-1234567890abcdef"
    result = scrub_pii(message)

    assert "sk-1234567890abcdef" not in result
    assert "[REDACTED]" in result


def test_pii_scrubber_removes_secret():
    """Test that PII scrubber strips secret field."""
    message = "secret=my-secret-value"
    result = scrub_pii(message)

    assert "my-secret-value" not in result
    assert "[REDACTED]" in result


def test_pii_scrubber_preserves_safe_content():
    """Test that PII scrubber preserves safe log content."""
    message = "Job 550e8400-e29b-41d4-a716-446655440000 status: IN_PROGRESS at 2024-03-24T10:30:00Z"
    result = scrub_pii(message)

    # Should preserve UUIDs, status names, timestamps
    assert "550e8400-e29b-41d4-a716-446655440000" in result
    assert "IN_PROGRESS" in result
    assert "2024-03-24T10:30:00Z" in result


def test_pii_scrubber_preserves_metadata():
    """Test that PII scrubber preserves metadata fields."""
    message = "File upload: size=1024KB format=PDF status=UPLOADING"
    result = scrub_pii(message)

    # Should NOT redact these safe values
    assert "size=1024KB" in result
    assert "format=PDF" in result
    assert "status=UPLOADING" in result


def test_pii_scrubber_case_insensitive_credentials():
    """Test that PII scrubber is case-insensitive for credential keywords."""
    message = "PASSWORD=secret123 Token=abc KEY=xyz"
    result = scrub_pii(message)

    assert "secret123" not in result
    assert "abc" not in result
    assert "xyz" not in result
    assert "[REDACTED]" in result


def test_pii_scrubber_empty_string():
    """Test that PII scrubber handles empty strings."""
    result = scrub_pii("")
    assert result == ""


def test_pii_scrubber_no_pii():
    """Test that PII scrubber doesn't modify messages without PII."""
    message = "Job started successfully with 100 files"
    result = scrub_pii(message)

    assert result == message
