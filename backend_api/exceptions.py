"""
Custom exceptions for Guardian backend.
"""


class GuardianException(Exception):
    """Base exception for Guardian backend."""
    pass


class InsufficientCreditsException(GuardianException):
    """Raised when tenant has insufficient credits."""
    
    def __init__(self, message: str, required: float = None, available: float = None, balance: dict = None):
        super().__init__(message)
        self.required = required
        self.available = available
        self.balance = balance


class CreditOperationException(GuardianException):
    """Raised when credit operation fails."""
    pass

