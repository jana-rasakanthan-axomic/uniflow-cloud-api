"""Exceptions package for UniFlow Cloud API."""


class InvalidSetupCodeError(Exception):
    """Raised when setup code is invalid."""
    pass


class SetupCodeExpiredError(Exception):
    """Raised when setup code has expired."""
    pass


class SetupCodeAlreadyUsedError(Exception):
    """Raised when setup code has already been used."""
    pass


class InvalidTokenError(Exception):
    """Raised when token is invalid."""
    pass


class RevokedTokenError(Exception):
    """Raised when token has been revoked."""
    pass
