"""
Logging API endpoints - MongoDB version.
"""

from fastapi import APIRouter, Depends, BackgroundTasks
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime

from ...core.mongodb import get_database
from ...core.auth import verify_api_key
from ...models.schemas import LogRequest, LogResponse
from ...models.mongodb_models import APILog, Incident, TenantConfig

router = APIRouter()


async def calculate_safety_units(log_data: LogRequest) -> float:
    """Calculate safety inference units consumed."""
    # 1 SIU per 100 tokens + 0.5 SIU per safety check
    token_units = (log_data.tokens_input + log_data.tokens_output) / 100
    check_units = 1.5  # Base checks (toxicity, bias, jailbreak)
    
    return token_units + check_units


async def create_incident_if_flagged(db: AsyncIOMotorDatabase, log_data: dict) -> str:
    """Create incident record for flagged content."""
    if not log_data.get("flagged"):
        return None
    
    # Determine incident type and severity
    incident_type = "toxicity"
    severity = "medium"
    
    toxicity_score = log_data.get("toxicity_score", 0.0)
    jailbreak_flag = log_data.get("jailbreak_flag", False)
    bias_flags = log_data.get("bias_flags", [])
    
    if toxicity_score > 0.8:
        incident_type = "toxicity"
        severity = "high" if toxicity_score > 0.9 else "medium"
    elif jailbreak_flag:
        incident_type = "jailbreak"
        severity = "critical"
    elif len(bias_flags) > 0:
        incident_type = "bias"
        severity = "medium"
    
    incident = Incident(
        tenant_id=log_data["tenant_id"],
        user_id=log_data["user_id"],
        incident_type=incident_type,
        severity=severity,
        status="pending",
        prompt=log_data["prompt"],
        response=log_data["response"],
        remediated_response=log_data.get("original_response"),
        toxicity_score=toxicity_score,
        bias_score=log_data.get("bias_score", 0.0),
        explanation=log_data.get("explanation"),
        log_id=str(log_data["_id"]),
    )
    
    result = await db.incidents.insert_one(incident.dict(by_alias=True, exclude={"id"}))
    return str(result.inserted_id)


@router.post("/log", response_model=LogResponse)
async def log_api_call(
    request: LogRequest,
    background_tasks: BackgroundTasks,
    tenant_id: str = Depends(verify_api_key),
    mongodb: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Log API call with safety analysis results.
    
    Creates log entry and incident if content is flagged.
    """
    # Calculate safety units
    safety_units = await calculate_safety_units(request)
    
    # Create log entry
    log = APILog(
        tenant_id=request.tenant_id,
        user_id=request.user_id,
        model=request.model,
        prompt=request.prompt,
        response=request.response,
        original_response=request.original_response,
        toxicity_score=request.safety_scores.get("toxicity_score", 0.0),
        toxicity_categories=request.safety_scores.get("toxicity_categories", []),
        bias_score=request.safety_scores.get("bias_score", 0.0),
        bias_flags=request.safety_scores.get("bias_flags", []),
        jailbreak_flag=request.safety_scores.get("jailbreak_flag", False),
        response_modification=request.safety_scores.get("response_modification", "none"),
        latency_ms=request.latency_ms,
        equitas_overhead_ms=request.equitas_overhead_ms,
        tokens_input=request.tokens_input,
        tokens_output=request.tokens_output,
        safety_units_used=safety_units,
        flagged=request.flagged,
        explanation=request.explanation,
    )
    
    result = await mongodb.api_logs.insert_one(log.dict(by_alias=True, exclude={"id"}))
    log_id = str(result.inserted_id)
    
    # Create incident if flagged
    incident_id = None
    if request.flagged:
        log_data = log.dict(by_alias=True)
        log_data["_id"] = result.inserted_id
        incident_id = await create_incident_if_flagged(mongodb, log_data)
    
    # Update tenant's safety units
    await mongodb.tenant_configs.update_one(
        {"tenant_id": request.tenant_id},
        {"$inc": {"safety_units_used": safety_units}},
        upsert=True
    )
    
    return LogResponse(
        success=True,
        log_id=log_id,  # Return MongoDB ObjectId as string
        incident_id=incident_id,  # Return MongoDB ObjectId as string
    )
