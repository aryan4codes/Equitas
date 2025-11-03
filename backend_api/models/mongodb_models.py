"""
MongoDB models for Equitas.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from bson import ObjectId


class PyObjectId(ObjectId):
    """Custom ObjectId type for Pydantic v2."""
    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type, _handler):
        from pydantic_core import core_schema
        return core_schema.json_or_python_schema(
            json_schema=core_schema.str_schema(),
            python_schema=core_schema.union_schema([
                core_schema.is_instance_schema(ObjectId),
                core_schema.chain_schema([
                    core_schema.str_schema(),
                    core_schema.no_info_plain_validator_function(cls.validate),
                ])
            ]),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda x: str(x)
            ),
        )

    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return v
        if isinstance(v, str):
            if ObjectId.is_valid(v):
                return ObjectId(v)
            raise ValueError("Invalid ObjectId")
        raise ValueError("Invalid ObjectId")


# User Models
class User(BaseModel):
    """User model linked to Clerk."""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    clerk_user_id: str = Field(..., unique=True, index=True)
    email: str
    name: Optional[str] = None
    tenant_id: str = Field(..., index=True)  # Each user belongs to a tenant
    role: str = Field(default="user")  # user, admin
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
    }


class APIKey(BaseModel):
    """API Key model."""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    key_hash: str = Field(..., index=True)  # Hashed API key
    key_prefix: str = Field(...)  # First 8 chars for display (eq_xxxxx)
    tenant_id: str = Field(..., index=True)
    user_id: str  # Clerk user ID who created it
    name: str  # User-friendly name
    is_active: bool = Field(default=True)
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
    }


class CreditRequest(BaseModel):
    """Credit request model."""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    tenant_id: str = Field(..., index=True)
    user_id: str  # Clerk user ID who requested
    amount: float = Field(..., gt=0)
    reason: Optional[str] = None
    status: str = Field(default="pending", index=True)  # pending, approved, rejected
    reviewed_by: Optional[str] = None  # Admin user ID
    reviewed_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
    }


# Tenant Config Model (MongoDB version)
class TenantConfig(BaseModel):
    """Per-tenant configuration."""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    tenant_id: str = Field(..., unique=True, index=True)
    
    # Safety thresholds
    toxicity_threshold: float = Field(default=0.7)
    bias_threshold: float = Field(default=0.3)
    
    # Feature flags
    enable_toxicity_check: bool = Field(default=True)
    enable_bias_check: bool = Field(default=True)
    enable_jailbreak_check: bool = Field(default=True)
    enable_remediation: bool = Field(default=True)
    enable_logging: bool = Field(default=True)
    
    # Privacy settings
    anonymize_prompts: bool = Field(default=False)
    retention_days: int = Field(default=90)
    
    # Credits
    credit_balance: float = Field(default=0.0)
    safety_units_limit: float = Field(default=10000.0)
    safety_units_used: float = Field(default=0.0)
    credit_enabled: bool = Field(default=True)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
    }


# Credit Transaction Model (MongoDB version)
class CreditTransaction(BaseModel):
    """Credit transaction model."""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    tenant_id: str = Field(..., index=True)
    transaction_type: str = Field(..., index=True)  # add, deduct, refund, expire
    amount: float  # Positive for add/refund, negative for deduct/expire
    balance_before: float
    balance_after: float
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    description: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    created_by: Optional[str] = None  # Admin user ID

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
    }


# API Log Model (MongoDB version)
class APILog(BaseModel):
    """Log of all API calls with safety analysis."""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    tenant_id: str = Field(..., index=True)
    user_id: str = Field(..., index=True)
    
    # Request info
    model: str
    prompt: str
    response: str
    original_response: Optional[str] = None
    
    # Safety scores
    toxicity_score: float = Field(default=0.0)
    toxicity_categories: List[str] = Field(default_factory=list)
    bias_score: float = Field(default=0.0)
    bias_flags: List[str] = Field(default_factory=list)
    jailbreak_flag: bool = Field(default=False)
    response_modification: str = Field(default="none")
    
    # Metrics
    latency_ms: float = Field(default=0.0)
    equitas_overhead_ms: float = Field(default=0.0)
    tokens_input: int = Field(default=0)
    tokens_output: int = Field(default=0)
    safety_units_used: float = Field(default=0.0)
    
    # Flags
    flagged: bool = Field(default=False, index=True)
    explanation: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
    }


# Incident Model (MongoDB version)
class Incident(BaseModel):
    """Flagged safety incidents."""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    tenant_id: str = Field(..., index=True)
    user_id: str
    
    # Incident details
    incident_type: str = Field(..., index=True)  # toxicity, bias, jailbreak
    severity: str  # low, medium, high, critical
    status: str = Field(default="pending")  # pending, reviewed, resolved, false_positive
    
    # Content
    prompt: str
    response: str
    remediated_response: Optional[str] = None
    
    # Scores
    toxicity_score: float = Field(default=0.0)
    bias_score: float = Field(default=0.0)
    
    # Explanation
    explanation: Optional[str] = None
    flagged_spans: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Reference to log
    log_id: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
    }


# Tenant Metrics Model (MongoDB version)
class TenantMetrics(BaseModel):
    """Aggregated metrics per tenant."""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    tenant_id: str = Field(..., index=True)
    
    # Time period
    period_start: datetime
    period_end: datetime
    period_type: str  # hour, day, week, month
    
    # Usage metrics
    total_calls: int = Field(default=0)
    flagged_calls: int = Field(default=0)
    blocked_calls: int = Field(default=0)
    remediated_calls: int = Field(default=0)
    
    # Safety metrics
    avg_toxicity_score: float = Field(default=0.0)
    avg_bias_score: float = Field(default=0.0)
    jailbreak_attempts: int = Field(default=0)
    
    # Performance metrics
    avg_latency_ms: float = Field(default=0.0)
    avg_overhead_ms: float = Field(default=0.0)
    
    # Usage
    total_tokens_input: int = Field(default=0)
    total_tokens_output: int = Field(default=0)
    total_safety_units: float = Field(default=0.0)
    
    # Breakdown by category
    incidents_by_category: Dict[str, int] = Field(default_factory=dict)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
    }

