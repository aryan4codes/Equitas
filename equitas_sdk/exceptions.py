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


class InsufficientCreditsException(equitasException):
    """Raised when tenant has insufficient credits."""
    
    def __init__(self, message: str, required: float = None, available: float = None, balance: dict = None):
        super().__init__(message)
        self.required = required
        self.available = available
        self.balance = balance
