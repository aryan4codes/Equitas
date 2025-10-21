"""
Logging API endpoints.
"""

from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ...core.database import get_db
from ...core.auth import verify_api_key
from ...models.schemas import LogRequest, LogResponse
from ...models.database import APILog, Incident, TenantConfig

router = APIRouter()


async def calculate_safety_units(log_data: LogRequest) -> float:
    """Calculate safety inference units consumed."""
    # 1 SIU per 100 tokens + 0.5 SIU per safety check
    token_units = (log_data.tokens_input + log_data.tokens_output) / 100
    check_units = 1.5  # Base checks (toxicity, bias, jailbreak)
    
    return token_units + check_units


async def create_incident_if_flagged(db: AsyncSession, log: APILog):
    """Create incident record for flagged content."""
    if not log.flagged:
        return None
    
    # Determine incident type and severity
    incident_type = "toxicity"
    severity = "medium"
    
    if log.toxicity_score > 0.8:
        incident_type = "toxicity"
        severity = "high" if log.toxicity_score > 0.9 else "medium"
    elif log.jailbreak_flag:
        incident_type = "jailbreak"
        severity = "critical"
    elif len(log.bias_flags) > 0:
        incident_type = "bias"
        severity = "medium"
    
    incident = Incident(
        tenant_id=log.tenant_id,
        user_id=log.user_id,
        incident_type=incident_type,
        severity=severity,
        status="pending",
        prompt=log.prompt,
        response=log.response,
        remediated_response=log.original_response if log.original_response else None,
        toxicity_score=log.toxicity_score,
        bias_score=log.bias_score,
        explanation=log.explanation,
        log_id=log.id,
    )
    
    db.add(incident)
    await db.flush()
    
    return incident.id


@router.post("/log", response_model=LogResponse)
async def log_api_call(
    request: LogRequest,
    background_tasks: BackgroundTasks,
    tenant_id: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
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
    
    db.add(log)
    await db.flush()
    
    # Create incident if flagged
    incident_id = await create_incident_if_flagged(db, log)
    
    # Update tenant's safety units
    stmt = select(TenantConfig).where(TenantConfig.tenant_id == request.tenant_id)
    result = await db.execute(stmt)
    tenant_config = result.scalar_one_or_none()
    
    if tenant_config:
        tenant_config.safety_units_used += safety_units
    
    await db.commit()
    
    return LogResponse(
        success=True,
        log_id=log.id,
        incident_id=incident_id,
    )
