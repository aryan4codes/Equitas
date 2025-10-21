"""
Metrics API endpoints.
"""

from datetime import datetime, timedelta
from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from ...core.database import get_db
from ...core.auth import verify_api_key
from ...models.schemas import MetricsQuery, MetricsResponse
from ...models.database import APILog, Incident

router = APIRouter()


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    tenant_id: str = Depends(verify_api_key),
    start_date: datetime = Query(None),
    end_date: datetime = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Get aggregated metrics for tenant.
    
    Returns usage, safety scores, and incident counts.
    """
    # Default to last 24 hours if not specified
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=1)
    
    # Query logs in time range
    stmt = select(APILog).where(
        APILog.tenant_id == tenant_id,
        APILog.created_at >= start_date,
        APILog.created_at <= end_date,
    )
    result = await db.execute(stmt)
    logs = result.scalars().all()
    
    # Calculate metrics
    total_calls = len(logs)
    flagged_calls = sum(1 for log in logs if log.flagged)
    
    avg_toxicity = (
        sum(log.toxicity_score for log in logs) / total_calls
        if total_calls > 0 else 0.0
    )
    avg_bias = (
        sum(log.bias_score for log in logs) / total_calls
        if total_calls > 0 else 0.0
    )
    avg_latency = (
        sum(log.latency_ms for log in logs) / total_calls
        if total_calls > 0 else 0.0
    )
    
    safety_units = sum(log.safety_units_used for log in logs)
    
    # Count incidents by category
    incidents_stmt = select(Incident).where(
        Incident.tenant_id == tenant_id,
        Incident.created_at >= start_date,
        Incident.created_at <= end_date,
    )
    incidents_result = await db.execute(incidents_stmt)
    incidents = incidents_result.scalars().all()
    
    incidents_by_category = {}
    for incident in incidents:
        category = incident.incident_type
        incidents_by_category[category] = incidents_by_category.get(category, 0) + 1
    
    return MetricsResponse(
        tenant_id=tenant_id,
        period_start=start_date,
        period_end=end_date,
        total_calls=total_calls,
        flagged_calls=flagged_calls,
        avg_toxicity_score=avg_toxicity,
        avg_bias_score=avg_bias,
        avg_latency_ms=avg_latency,
        safety_units_used=safety_units,
        incidents_by_category=incidents_by_category,
    )
