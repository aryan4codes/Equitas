"""
Incidents API endpoints.
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from ...core.database import get_db
from ...core.auth import verify_api_key
from ...models.schemas import IncidentQuery, IncidentResponse, IncidentListResponse
from ...models.database import Incident

router = APIRouter()


@router.get("/incidents", response_model=IncidentListResponse)
async def get_incidents(
    tenant_id: str = Depends(verify_api_key),
    incident_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    Query incidents with filters.
    
    Returns paginated list of flagged safety incidents.
    """
    # Build query
    stmt = select(Incident).where(Incident.tenant_id == tenant_id)
    
    if incident_type:
        stmt = stmt.where(Incident.incident_type == incident_type)
    if severity:
        stmt = stmt.where(Incident.severity == severity)
    if status:
        stmt = stmt.where(Incident.status == status)
    if start_date:
        stmt = stmt.where(Incident.created_at >= start_date)
    if end_date:
        stmt = stmt.where(Incident.created_at <= end_date)
    
    # Get total count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0
    
    # Apply pagination and ordering
    stmt = stmt.order_by(Incident.created_at.desc()).offset(offset).limit(limit)
    
    # Execute query
    result = await db.execute(stmt)
    incidents = result.scalars().all()
    
    # Convert to response models
    items = [
        IncidentResponse(
            id=inc.id,
            tenant_id=inc.tenant_id,
            user_id=inc.user_id,
            incident_type=inc.incident_type,
            severity=inc.severity,
            status=inc.status,
            prompt=inc.prompt,
            response=inc.response,
            remediated_response=inc.remediated_response,
            toxicity_score=inc.toxicity_score,
            bias_score=inc.bias_score,
            explanation=inc.explanation,
            created_at=inc.created_at,
        )
        for inc in incidents
    ]
    
    return IncidentListResponse(
        total=total,
        items=items,
        limit=limit,
        offset=offset,
    )


@router.get("/incidents/{incident_id}", response_model=IncidentResponse)
async def get_incident_detail(
    incident_id: int,
    tenant_id: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed information about a specific incident.
    """
    stmt = select(Incident).where(
        Incident.id == incident_id,
        Incident.tenant_id == tenant_id,
    )
    result = await db.execute(stmt)
    incident = result.scalar_one_or_none()
    
    if not incident:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Incident not found")
    
    return IncidentResponse(
        id=incident.id,
        tenant_id=incident.tenant_id,
        user_id=incident.user_id,
        incident_type=incident.incident_type,
        severity=incident.severity,
        status=incident.status,
        prompt=incident.prompt,
        response=incident.response,
        remediated_response=incident.remediated_response,
        toxicity_score=incident.toxicity_score,
        bias_score=incident.bias_score,
        explanation=incident.explanation,
        created_at=incident.created_at,
    )
