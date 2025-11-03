"""
Incidents API endpoints - MongoDB version.
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from bson.errors import InvalidId

from ...core.mongodb import get_database
from ...core.auth import verify_api_key
from ...models.schemas import IncidentQuery, IncidentResponse, IncidentListResponse

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
    mongodb: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Query incidents with filters.
    
    Returns paginated list of flagged safety incidents.
    """
    # Build query
    query = {"tenant_id": tenant_id}
    
    if incident_type:
        query["incident_type"] = incident_type
    if severity:
        query["severity"] = severity
    if status:
        query["status"] = status
    
    date_filter = {}
    if start_date:
        date_filter["$gte"] = start_date
    if end_date:
        date_filter["$lte"] = end_date
    if date_filter:
        query["created_at"] = date_filter
    
    # Get total count
    total = await mongodb.incidents.count_documents(query)
    
    # Execute query with pagination
    cursor = mongodb.incidents.find(query).sort("created_at", -1).skip(offset).limit(limit)
    incidents = await cursor.to_list(length=limit)
    
    # Convert to response models
    items = []
    for inc in incidents:
        items.append(
        IncidentResponse(
                id=str(inc["_id"]),  # Use MongoDB ObjectId as string
                tenant_id=inc["tenant_id"],
                user_id=inc["user_id"],
                incident_type=inc["incident_type"],
                severity=inc["severity"],
                status=inc.get("status", "pending"),
                prompt=inc["prompt"],
                response=inc["response"],
                remediated_response=inc.get("remediated_response"),
                toxicity_score=inc.get("toxicity_score", 0.0),
                bias_score=inc.get("bias_score", 0.0),
                explanation=inc.get("explanation"),
                created_at=inc["created_at"] if isinstance(inc["created_at"], datetime) else datetime.utcnow(),
            )
        )
    
    return IncidentListResponse(
        total=total,
        items=items,
        limit=limit,
        offset=offset,
    )


@router.get("/incidents/{incident_id}", response_model=IncidentResponse)
async def get_incident_detail(
    incident_id: str,
    tenant_id: str = Depends(verify_api_key),
    mongodb: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Get detailed information about a specific incident.
    """
    try:
        # Try to parse as ObjectId first
        if len(incident_id) == 24:
            query = {"_id": ObjectId(incident_id), "tenant_id": tenant_id}
        else:
            # Fallback: search by any field that might match
            query = {"tenant_id": tenant_id}  # Would need better ID mapping
            raise HTTPException(status_code=404, detail="Invalid incident ID format")
    except (InvalidId, ValueError):
        raise HTTPException(status_code=400, detail="Invalid incident ID format")
    
    incident = await mongodb.incidents.find_one(query)
    
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    return IncidentResponse(
        id=str(incident["_id"]),  # Use MongoDB ObjectId as string
        tenant_id=incident["tenant_id"],
        user_id=incident["user_id"],
        incident_type=incident["incident_type"],
        severity=incident["severity"],
        status=incident.get("status", "pending"),
        prompt=incident["prompt"],
        response=incident["response"],
        remediated_response=incident.get("remediated_response"),
        toxicity_score=incident.get("toxicity_score", 0.0),
        bias_score=incident.get("bias_score", 0.0),
        explanation=incident.get("explanation"),
        created_at=incident["created_at"] if isinstance(incident["created_at"], datetime) else datetime.utcnow(),
    )
