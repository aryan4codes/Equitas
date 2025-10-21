"""
Pydantic schemas for API requests/responses.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


# Analysis Requests/Responses

class ToxicityRequest(BaseModel):
    """Request for toxicity analysis."""
    text: str = Field(..., description="Text to analyze")
    tenant_id: str = Field(..., description="Tenant identifier")


class ToxicityResponse(BaseModel):
    """Response from toxicity analysis."""
    toxicity_score: float = Field(..., ge=0.0, le=1.0)
    flagged: bool
    categories: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class BiasRequest(BaseModel):
    """Request for bias analysis."""
    prompt: str = Field(..., description="Original prompt")
    response: str = Field(..., description="LLM response")
    tenant_id: str = Field(..., description="Tenant identifier")
    variants: Optional[List[str]] = None


class BiasResponse(BaseModel):
    """Response from bias analysis."""
    bias_score: float = Field(..., ge=0.0, le=1.0)
    flags: List[str] = Field(default_factory=list)
    details: Optional[Dict[str, Any]] = None


class JailbreakRequest(BaseModel):
    """Request for jailbreak detection."""
    text: str = Field(..., description="Text to analyze")
    tenant_id: str = Field(..., description="Tenant identifier")


class JailbreakResponse(BaseModel):
    """Response from jailbreak detection."""
    jailbreak_flag: bool
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    patterns_detected: List[str] = Field(default_factory=list)


class ExplainRequest(BaseModel):
    """Request for explanation."""
    text: str
    issues: List[str] = Field(..., description="Issues to explain: toxicity, bias, jailbreak")
    tenant_id: str


class ExplainResponse(BaseModel):
    """Response with explanation."""
    explanation: str
    highlighted_spans: List[Dict[str, Any]] = Field(default_factory=list)


class RemediateRequest(BaseModel):
    """Request for content remediation."""
    text: str = Field(..., description="Text to remediate")
    issue: str = Field(..., description="Issue type: toxicity, bias")
    tenant_id: str


class RemediateResponse(BaseModel):
    """Response with remediated content."""
    remediated_text: str
    original_score: float
    new_score: float
    changes_made: List[str] = Field(default_factory=list)


# Logging

class LogRequest(BaseModel):
    """Request to log API call."""
    tenant_id: str
    user_id: str
    model: str
    prompt: str
    response: str
    original_response: Optional[str] = None
    safety_scores: Dict[str, Any]
    latency_ms: float
    equitas_overhead_ms: float
    tokens_input: int
    tokens_output: int
    timestamp: float
    flagged: bool
    explanation: Optional[str] = None


class LogResponse(BaseModel):
    """Response from logging."""
    success: bool
    log_id: Optional[int] = None
    incident_id: Optional[int] = None


# Metrics

class MetricsQuery(BaseModel):
    """Query parameters for metrics."""
    tenant_id: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    period: Literal["hour", "day", "week", "month"] = "day"


class MetricsResponse(BaseModel):
    """Aggregated metrics response."""
    tenant_id: str
    period_start: datetime
    period_end: datetime
    total_calls: int
    flagged_calls: int
    avg_toxicity_score: float
    avg_bias_score: float
    avg_latency_ms: float
    safety_units_used: float
    incidents_by_category: Dict[str, int]


# Incidents

class IncidentQuery(BaseModel):
    """Query parameters for incidents."""
    tenant_id: str
    incident_type: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(default=100, le=1000)
    offset: int = Field(default=0, ge=0)


class IncidentResponse(BaseModel):
    """Incident details."""
    id: int
    tenant_id: str
    user_id: str
    incident_type: str
    severity: str
    status: str
    prompt: str
    response: str
    remediated_response: Optional[str]
    toxicity_score: float
    bias_score: float
    explanation: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class IncidentListResponse(BaseModel):
    """List of incidents with pagination."""
    total: int
    items: List[IncidentResponse]
    limit: int
    offset: int
