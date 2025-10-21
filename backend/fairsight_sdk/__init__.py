"""
FairSight SDK - Client library for safety-enhanced OpenAI API calls.

This SDK wraps OpenAI's API to provide:
- Automatic safety checks (toxicity, bias, jailbreaks)
- Real-time logging and observability
- Automatic remediation of unsafe content
- Multi-tenant support
"""

from .client import FairSight
from .models import SafeCompletionResponse, SafetyConfig, SafetyScores
from .exceptions import (
    FairSightException,
    SafetyViolationException,
    RemediationFailedException,
)

__version__ = "0.1.0"

__all__ = [
    "FairSight",
    "SafeCompletionResponse",
    "SafetyConfig",
    "SafetyScores",
    "FairSightException",
    "SafetyViolationException",
    "RemediationFailedException",
]
