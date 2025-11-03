"""
User management API endpoints.
"""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from bson import ObjectId
from bson.errors import InvalidId

from ...core.mongodb import get_database
from ...core.auth import verify_clerk_token, get_current_user_id
from ...models.mongodb_models import User
from ...models.schemas import CreditBalanceResponse, MetricsResponse, IncidentListResponse, IncidentResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

router = APIRouter()


class RegisterRequest(BaseModel):
    email: str
    name: Optional[str] = None


@router.post("/register")
async def register_user(
    request: RegisterRequest,
    clerk_user_id: str = Depends(get_current_user_id),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Register a new user (called after Clerk signup).
    Creates a tenant_id based on user ID.
    """
    # Check if user already exists
    existing_user = await db.users.find_one({"clerk_user_id": clerk_user_id})
    if existing_user:
        return {
            "success": True,
            "user_id": str(existing_user["_id"]),
            "tenant_id": existing_user["tenant_id"],
            "message": "User already registered",
        }
    
    # Create tenant_id from user_id (or use user_id directly)
    tenant_id = f"tenant_{clerk_user_id[:8]}"
    
    user = User(
        clerk_user_id=clerk_user_id,
        email=request.email,
        name=request.name,
        tenant_id=tenant_id,
        role="user",
    )
    
    result = await db.users.insert_one(user.dict(by_alias=True, exclude={"id"}))
    
    # Create default tenant config
    from ...models.mongodb_models import TenantConfig
    default_config = TenantConfig(
        tenant_id=tenant_id,
        credit_balance=0.0,
        credit_enabled=True,
    )
    await db.tenant_configs.insert_one(default_config.dict(by_alias=True, exclude={"id"}))
    
    return {
        "success": True,
        "user_id": str(result.inserted_id),
        "tenant_id": tenant_id,
    }


@router.get("/me")
async def get_current_user(
    clerk_user_id: str = Depends(get_current_user_id),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Get current user information."""
    user = await db.users.find_one({"clerk_user_id": clerk_user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": str(user["_id"]),
        "clerk_user_id": user["clerk_user_id"],
        "email": user["email"],
        "name": user.get("name"),
        "tenant_id": user["tenant_id"],
        "role": user.get("role", "user"),
    }


@router.get("/balance")
async def get_user_balance(
    clerk_user_id: str = Depends(get_current_user_id),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Get credit balance for current user."""
    user = await db.users.find_one({"clerk_user_id": clerk_user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    from ...services.mongodb_credit_manager import MongoCreditManager
    credit_manager = MongoCreditManager(db)
    balance = await credit_manager.get_balance(user["tenant_id"])
    
    return CreditBalanceResponse(**balance)


@router.get("/metrics")
async def get_user_metrics(
    clerk_user_id: str = Depends(get_current_user_id),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Get aggregated metrics for current user's tenant.
    
    Returns usage, safety scores, and incident counts.
    """
    user = await db.users.find_one({"clerk_user_id": clerk_user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    tenant_id = user["tenant_id"]
    
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
    
    cursor = db.api_logs.find(query)
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
    incidents_cursor = db.incidents.find(incidents_query)
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


@router.get("/logs")
async def get_user_logs(
    clerk_user_id: str = Depends(get_current_user_id),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    flagged_only: bool = Query(False),
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Get API logs for current user's tenant.
    
    Returns detailed log entries with safety analysis.
    """
    user = await db.users.find_one({"clerk_user_id": clerk_user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    tenant_id = user["tenant_id"]
    
    # Build query
    query = {"tenant_id": tenant_id}
    
    if flagged_only:
        query["flagged"] = True
    
    date_filter = {}
    if start_date:
        date_filter["$gte"] = start_date
    if end_date:
        date_filter["$lte"] = end_date
    if date_filter:
        query["created_at"] = date_filter
    
    # Get total count
    total = await db.api_logs.count_documents(query)
    
    # Execute query with pagination
    cursor = db.api_logs.find(query).sort("created_at", -1).skip(offset).limit(limit)
    logs = await cursor.to_list(length=limit)
    
    # Format response
    items = []
    for log in logs:
        items.append({
            "id": str(log["_id"]),
            "tenant_id": log["tenant_id"],
            "user_id": log["user_id"],
            "model": log.get("model", ""),
            "prompt": log.get("prompt", ""),
            "response": log.get("response", ""),
            "original_response": log.get("original_response"),
            "toxicity_score": log.get("toxicity_score", 0.0),
            "toxicity_categories": log.get("toxicity_categories", []),
            "bias_score": log.get("bias_score", 0.0),
            "bias_flags": log.get("bias_flags", []),
            "jailbreak_flag": log.get("jailbreak_flag", False),
            "response_modification": log.get("response_modification", "none"),
            "latency_ms": log.get("latency_ms", 0.0),
            "equitas_overhead_ms": log.get("equitas_overhead_ms", 0.0),
            "tokens_input": log.get("tokens_input", 0),
            "tokens_output": log.get("tokens_output", 0),
            "safety_units_used": log.get("safety_units_used", 0.0),
            "flagged": log.get("flagged", False),
            "explanation": log.get("explanation"),
            "created_at": log["created_at"].isoformat() if isinstance(log["created_at"], datetime) else log["created_at"],
        })
    
    return {
        "total": total,
        "items": items,
        "limit": limit,
        "offset": offset,
    }


@router.get("/incidents")
async def get_user_incidents(
    clerk_user_id: str = Depends(get_current_user_id),
    incident_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Get incidents for current user's tenant.
    
    Returns flagged safety incidents.
    """
    user = await db.users.find_one({"clerk_user_id": clerk_user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    tenant_id = user["tenant_id"]
    
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
    total = await db.incidents.count_documents(query)
    
    # Execute query with pagination
    cursor = db.incidents.find(query).sort("created_at", -1).skip(offset).limit(limit)
    incidents = await cursor.to_list(length=limit)
    
    # Convert to response models
    items = []
    for inc in incidents:
        items.append(
            IncidentResponse(
                id=str(inc["_id"]),
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


@router.get("/logs/{log_id}")
async def get_log_detail(
    log_id: str,
    clerk_user_id: str = Depends(get_current_user_id),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Get detailed information about a specific log entry.
    """
    user = await db.users.find_one({"clerk_user_id": clerk_user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    tenant_id = user["tenant_id"]
    
    try:
        query = {"_id": ObjectId(log_id), "tenant_id": tenant_id}
    except (InvalidId, ValueError):
        raise HTTPException(status_code=400, detail="Invalid log ID format")
    
    log = await db.api_logs.find_one(query)
    
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    
    return {
        "id": str(log["_id"]),
        "tenant_id": log["tenant_id"],
        "user_id": log["user_id"],
        "model": log.get("model", ""),
        "prompt": log.get("prompt", ""),
        "response": log.get("response", ""),
        "original_response": log.get("original_response"),
        "toxicity_score": log.get("toxicity_score", 0.0),
        "toxicity_categories": log.get("toxicity_categories", []),
        "bias_score": log.get("bias_score", 0.0),
        "bias_flags": log.get("bias_flags", []),
        "jailbreak_flag": log.get("jailbreak_flag", False),
        "response_modification": log.get("response_modification", "none"),
        "latency_ms": log.get("latency_ms", 0.0),
        "equitas_overhead_ms": log.get("equitas_overhead_ms", 0.0),
        "tokens_input": log.get("tokens_input", 0),
        "tokens_output": log.get("tokens_output", 0),
        "safety_units_used": log.get("safety_units_used", 0.0),
        "flagged": log.get("flagged", False),
        "explanation": log.get("explanation"),
        "created_at": log["created_at"].isoformat() if isinstance(log["created_at"], datetime) else log["created_at"],
    }
