"""
Metrics API endpoints - MongoDB version.
"""

from datetime import datetime, timedelta
from typing import List
from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from ...core.mongodb import get_database
from ...core.auth import verify_api_key
from ...models.schemas import MetricsQuery, MetricsResponse

router = APIRouter()


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    tenant_id: str = Depends(verify_api_key),
    start_date: datetime = Query(None),
    end_date: datetime = Query(None),
    mongodb: AsyncIOMotorDatabase = Depends(get_database),
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
    query = {
        "tenant_id": tenant_id,
        "created_at": {
            "$gte": start_date,
            "$lte": end_date,
        }
    }
    
    cursor = mongodb.api_logs.find(query)
    logs = await cursor.to_list(length=10000)  # Limit to prevent memory issues
    
    # Calculate metrics
    total_calls = len(logs)
    flagged_calls = sum(1 for log in logs if log.get("flagged", False))
    
    avg_toxicity = (
        sum(log.get("toxicity_score", 0.0) for log in logs) / total_calls
        if total_calls > 0 else 0.0
    )
    avg_bias = (
        sum(log.get("bias_score", 0.0) for log in logs) / total_calls
        if total_calls > 0 else 0.0
    )
    avg_latency = (
        sum(log.get("latency_ms", 0.0) for log in logs) / total_calls
        if total_calls > 0 else 0.0
    )
    
    safety_units = sum(log.get("safety_units_used", 0.0) for log in logs)
    
    # Count incidents by category
    incidents_query = {
        "tenant_id": tenant_id,
        "created_at": {
            "$gte": start_date,
            "$lte": end_date,
        }
    }
    incidents_cursor = mongodb.incidents.find(incidents_query)
    incidents = await incidents_cursor.to_list(length=10000)
    
    incidents_by_category = {}
    for incident in incidents:
        category = incident.get("incident_type", "unknown")
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
