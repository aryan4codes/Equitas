"""
Custom exceptions for equitas SDK.
"""


class equitasException(Exception):
    """Base exception for equitas SDK."""
    pass


class SafetyViolationException(equitasException):
    """Raised when safety violation is detected and on_flag='strict'."""
    pass


class RemediationFailedException(equitasException):
    """Raised when automatic remediation fails."""
    pass


class GuardianAPIException(equitasException):
    """Raised when Guardian backend API call fails."""
    pass
