"""
Custom exceptions for FairSight SDK.
"""


class FairSightException(Exception):
    """Base exception for FairSight SDK."""
    pass


class SafetyViolationException(FairSightException):
    """Raised when safety violation is detected and on_flag='strict'."""
    pass


class RemediationFailedException(FairSightException):
    """Raised when automatic remediation fails."""
    pass


class GuardianAPIException(FairSightException):
    """Raised when Guardian backend API call fails."""
    pass
