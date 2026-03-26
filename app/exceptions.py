"""Custom exceptions for UniFlow API."""


class InvalidSetupCodeError(Exception):
    """Raised when setup code is invalid, expired, or already used.

    This exception is used by the device linking flow when a setup code
    cannot be validated for any reason (not found, expired, or already used).
    The specific reason is logged in the audit trail but not exposed to the client.
    """

    pass


class SetupCodeExpiredError(InvalidSetupCodeError):
    """Raised when setup code has expired."""

    pass


class SetupCodeAlreadyUsedError(InvalidSetupCodeError):
    """Raised when setup code has already been used."""

    pass


class InvalidTokenError(Exception):
    """Raised when a refresh token is invalid or expired.

    This exception is used by the token refresh flow when a token cannot
    be verified (invalid signature, expired, malformed, or not found in database).
    """

    pass


class RevokedTokenError(Exception):
    """Raised when a refresh token has been revoked (reuse detected).

    This exception indicates that a token that was previously used is being
    presented again, which signals a potential security breach. The entire
    token chain should be revoked and the device set offline.
    """

    pass
