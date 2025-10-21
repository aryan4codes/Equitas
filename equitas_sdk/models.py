"""
Data models for equitas SDK.
"""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field
from openai.types.chat import ChatCompletion


class SafetyConfig(BaseModel):
    """Configuration for safety checks."""
    
    on_flag: Literal["strict", "auto-correct", "warn-only"] = Field(
        default="warn-only",
        description="Action to take when safety violation is detected"
    )
    toxicity_threshold: float = Field(
        default=0.7,
        description="Threshold for toxicity score (0-1)"
    )
    enable_bias_check: bool = Field(default=True)
    enable_jailbreak_check: bool = Field(default=True)
    enable_remediation: bool = Field(default=True)


class SafetyScores(BaseModel):
    """Safety analysis scores for a response."""
    
    toxicity_score: float = Field(
        default=0.0,
        description="Toxicity score from 0 (safe) to 1 (toxic)"
    )
    toxicity_categories: List[str] = Field(
        default_factory=list,
        description="Triggered moderation categories (hate, harassment, violence, etc.)"
    )
    bias_flags: List[str] = Field(
        default_factory=list,
        description="Detected bias issues (gender_bias, racial_bias, etc.)"
    )
    jailbreak_flag: bool = Field(
        default=False,
        description="Whether jailbreak/prompt injection detected"
    )
    response_modification: Literal["none", "rephrased", "blocked"] = Field(
        default="none",
        description="Type of modification applied to response"
    )


class SafeCompletionResponse(BaseModel):
    """
    Enhanced ChatCompletion response with safety metadata.
    
    This extends OpenAI's ChatCompletion with additional safety fields.
    """
    
    # Standard OpenAI fields
    id: str
    object: str
    created: int
    model: str
    choices: List[Any]
    usage: Optional[Any] = None
    
    # equitas safety fields
    safety_scores: SafetyScores
    explanation: Optional[str] = Field(
        default=None,
        description="Explanation of safety issues if any"
    )
    latency_ms: float = Field(
        default=0.0,
        description="Total latency including equitas processing"
    )
    
    class Config:
        arbitrary_types_allowed = True

    def to_openai_format(self) -> Dict[str, Any]:
        """Convert to standard OpenAI response format (without safety fields)."""
        return {
            "id": self.id,
            "object": self.object,
            "created": self.created,
            "model": self.model,
            "choices": self.choices,
            "usage": self.usage,
        }
