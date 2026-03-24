"""OpenAsset API exceptions."""


class OAAPIError(Exception):
    """Base exception for OpenAsset API errors.

    Raised when the OA API returns an error response that is not a rate limit.
    """

    pass


class OARateLimitError(OAAPIError):
    """Raised when OA API rate limit is exceeded after retries.

    This exception indicates that the API returned 429 (Too Many Requests)
    and all retry attempts (with exponential backoff) have been exhausted.
    The job should transition to RATE_LIMITED state and alert operations.
    """

    pass


class OAConnectionError(OAAPIError):
    """Raised when unable to connect to OA API.

    This exception indicates network connectivity issues or OA API unavailability.
    """

    pass
