"""
Database models for equitas Guardian.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, Text, Index
from sqlalchemy.sql import func

from ..core.database import Base


class APILog(Base):
    """Log of all API calls with safety analysis."""
    
    __tablename__ = "api_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    
    # Request info
    model = Column(String(100), nullable=False)
    prompt = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    original_response = Column(Text, nullable=True)
    
    # Safety scores
    toxicity_score = Column(Float, default=0.0)
    toxicity_categories = Column(JSON, default=list)
    bias_score = Column(Float, default=0.0)
    bias_flags = Column(JSON, default=list)
    jailbreak_flag = Column(Boolean, default=False)
    response_modification = Column(String(50), default="none")
    
    # Metrics
    latency_ms = Column(Float, default=0.0)
    equitas_overhead_ms = Column(Float, default=0.0)
    tokens_input = Column(Integer, default=0)
    tokens_output = Column(Integer, default=0)
    safety_units_used = Column(Float, default=0.0)
    
    # Flags
    flagged = Column(Boolean, default=False, index=True)
    explanation = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Indexes for common queries
    __table_args__ = (
        Index('ix_tenant_created', 'tenant_id', 'created_at'),
        Index('ix_tenant_flagged', 'tenant_id', 'flagged'),
    )


class Incident(Base):
    """Flagged safety incidents."""
    
    __tablename__ = "incidents"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    user_id = Column(String(100), nullable=False)
    
    # Incident details
    incident_type = Column(String(50), nullable=False, index=True)  # toxicity, bias, jailbreak
    severity = Column(String(20), nullable=False)  # low, medium, high, critical
    status = Column(String(20), default="pending")  # pending, reviewed, resolved, false_positive
    
    # Content
    prompt = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    remediated_response = Column(Text, nullable=True)
    
    # Scores
    toxicity_score = Column(Float, default=0.0)
    bias_score = Column(Float, default=0.0)
    
    # Explanation
    explanation = Column(Text, nullable=True)
    flagged_spans = Column(JSON, default=list)
    
    # Reference to log
    log_id = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_by = Column(String(100), nullable=True)
    
    __table_args__ = (
        Index('ix_tenant_type_created', 'tenant_id', 'incident_type', 'created_at'),
    )


class TenantMetrics(Base):
    """Aggregated metrics per tenant."""
    
    __tablename__ = "tenant_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    
    # Time period
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    period_type = Column(String(20), nullable=False)  # hour, day, week, month
    
    # Usage metrics
    total_calls = Column(Integer, default=0)
    flagged_calls = Column(Integer, default=0)
    blocked_calls = Column(Integer, default=0)
    remediated_calls = Column(Integer, default=0)
    
    # Safety metrics
    avg_toxicity_score = Column(Float, default=0.0)
    avg_bias_score = Column(Float, default=0.0)
    jailbreak_attempts = Column(Integer, default=0)
    
    # Performance metrics
    avg_latency_ms = Column(Float, default=0.0)
    avg_overhead_ms = Column(Float, default=0.0)
    
    # Usage
    total_tokens_input = Column(Integer, default=0)
    total_tokens_output = Column(Integer, default=0)
    total_safety_units = Column(Float, default=0.0)
    
    # Breakdown by category
    incidents_by_category = Column(JSON, default=dict)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('ix_tenant_period', 'tenant_id', 'period_start', 'period_end'),
    )


class TenantConfig(Base):
    """Per-tenant configuration."""
    
    __tablename__ = "tenant_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), unique=True, nullable=False, index=True)
    
    # Safety thresholds
    toxicity_threshold = Column(Float, default=0.7)
    bias_threshold = Column(Float, default=0.3)
    
    # Feature flags
    enable_toxicity_check = Column(Boolean, default=True)
    enable_bias_check = Column(Boolean, default=True)
    enable_jailbreak_check = Column(Boolean, default=True)
    enable_remediation = Column(Boolean, default=True)
    enable_logging = Column(Boolean, default=True)
    
    # Privacy settings
    anonymize_prompts = Column(Boolean, default=False)
    retention_days = Column(Integer, default=90)
    
    # Credits
    safety_units_limit = Column(Float, default=10000.0)
    safety_units_used = Column(Float, default=0.0)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
