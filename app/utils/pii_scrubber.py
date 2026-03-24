"""PII scrubbing filter for cloud-side logging.

This module provides functionality to remove Personally Identifiable Information (PII)
from log messages before they are written to CloudWatch or other logging destinations.

The scrubber removes:
- Email addresses
- File paths (Windows and Unix)
- Credentials (password, token, key, secret fields)

Safe content like UUIDs, status names, timestamps, and metadata values are preserved.
"""

import re


def scrub_pii(log_message: str) -> str:
    """Remove PII from log messages.

    Args:
        log_message: The original log message string

    Returns:
        Scrubbed log message with PII replaced by [REDACTED]

    Examples:
        >>> scrub_pii("User john@example.com uploaded file")
        'User [REDACTED] uploaded file'

        >>> scrub_pii("File at C:\\Users\\John\\file.pdf")
        'File at [REDACTED]'

        >>> scrub_pii("password=secret123")
        '[REDACTED]'
    """
    if not log_message:
        return log_message

    # Email addresses
    # Pattern: name@domain.tld
    email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    scrubbed = re.sub(email_pattern, "[REDACTED]", log_message)

    # File paths (Windows and Unix)
    # Windows: C:\path\to\file or D:\path
    # Unix: /path/to/file
    file_path_pattern = r"([A-Za-z]:\\|\/)[^\s]+"
    scrubbed = re.sub(file_path_pattern, "[REDACTED]", scrubbed)

    # Credentials (password, token, key, secret)
    # Pattern: keyword followed by =, :, or space, then value
    credential_pattern = r"(password|token|key|secret)[\s=:]+[^\s]+"
    scrubbed = re.sub(credential_pattern, "[REDACTED]", scrubbed, flags=re.IGNORECASE)

    return scrubbed
