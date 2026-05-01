"""
Analysis API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
import asyncio
import time

from ...core.mongodb import get_database
from ...core.auth import verify_api_key
from ...services.mongodb_credit_manager import MongoCreditManager
from ...models.schemas import (
    ToxicityRequest, ToxicityResponse,
    BiasRequest, BiasResponse,
    JailbreakRequest, JailbreakResponse,
    ExplainRequest, ExplainResponse,
    RemediateRequest, RemediateResponse,
    HallucinationRequest, HallucinationResponse,
    DemoScanRequest, DemoScanResponse, DemoScanDetection,
)
from ...services.toxicity import ToxicityDetector  # Legacy fallback
from ...services.custom_toxicity import get_toxicity_detector  # Custom transformer detector
from ...services.detoxify_toxicity import get_detoxify_detector  # Detoxify detector
from ...services.bias import BiasDetector  # Legacy fallback
from ...services.enhanced_bias import get_bias_detector  # New enhanced detector
from ...services.jailbreak import JailbreakDetector  # Legacy fallback
from ...services.advanced_jailbreak import get_jailbreak_detector  # New advanced detector
from ...services.hallucination import get_hallucination_detector  # New hallucination detector
from ...services.explainability import ExplainabilityEngine
from ...services.remediation import RemediationEngine
from ...services.custom_classifiers import classifier_registry
from ...services.policy_engine import policy_engine
from ...services.advanced_bias import bias_test_suite
from ...exceptions import InsufficientCreditsException

router = APIRouter()

# Public routes (no API key) — mounted separately in main.py
public_analysis_router = APIRouter()


# Initialize services (use new detectors)
# Use Detoxify for toxicity detection (simpler, more maintainable)
toxicity_detector = get_detoxify_detector(model_name="original")  # Options: original, unbiased, multilingual
custom_toxicity_detector = get_toxicity_detector()  # Fallback option
enhanced_bias_detector = get_bias_detector()
advanced_jailbreak_detector = get_jailbreak_detector()
hallucination_detector = get_hallucination_detector()

# Legacy detectors (fallback)
legacy_toxicity_detector = ToxicityDetector()
legacy_bias_detector = BiasDetector()
legacy_jailbreak_detector = JailbreakDetector()
explainability_engine = ExplainabilityEngine()
remediation_engine = RemediationEngine()


def _demo_detection_severity(confidence: float, detected: bool) -> str:
    if confidence >= 0.7:
        return "critical"
    if confidence >= 0.4:
        return "high"
    if confidence >= 0.25 or detected:
        return "medium"
    if confidence > 0.1:
        return "low"
    return "safe"


@public_analysis_router.post("/demo-scan", response_model=DemoScanResponse)
async def demo_scan(request: DemoScanRequest) -> DemoScanResponse:
    """
    Public interactive demo: analyze a single prompt for jailbreak, toxicity, bias, and hallucination.
    Does not consume credits or require an API key (rate-limit at the edge in production).
    """
    start = time.perf_counter()
    text = request.text.strip()

    tox_r, jail_r, bias_r, hall_r = await asyncio.gather(
        toxicity_detector.analyze(text),
        advanced_jailbreak_detector.detect(text, None),
        enhanced_bias_detector.analyze_comprehensive(
            prompt=text,
            response=text,
            demographic_variants=None,
        ),
        hallucination_detector.detect(
            prompt=text,
            response=text,
            context=None,
        ),
    )

    tox_score = float(tox_r.get("toxicity_score", 0.0))
    tox_detected = bool(tox_r.get("flagged", False))

    jail_conf = float(jail_r.get("confidence", 0.0))
    # Treat as detected if the detector flagged it OR if confidence is moderately high
    jail_detected = bool(jail_r.get("jailbreak_flag", False)) or jail_conf >= 0.35
    comp = jail_r.get("components") or {}
    jail_patterns = list(comp.get("patterns_found") or [])

    bias_score = float(bias_r.get("bias_score", 0.0))
    bias_detected = bool(bias_r.get("bias_detected", False))

    hall_score = float(hall_r.get("hallucination_score", 0.0))
    hall_detected = bool(hall_r.get("flagged", False))

    jail_details = jail_r.get("explanation") or (
        "Potential jailbreak or prompt injection patterns detected."
        if jail_detected
        else "No strong jailbreak or injection signals detected."
    )
    tox_details = (
        "Content may be toxic or harmful based on model scores."
        if tox_detected
        else "No significant toxicity detected."
    )
    bias_details = (
        "Potential demographic bias or stereotyping signals."
        if bias_detected
        else "No strong bias signals detected for this text."
    )
    hall_details = (
        f"Hallucination risk score {hall_score:.2f} — review factual claims."
        if hall_detected or hall_score > 0.35
        else "Low hallucination risk for this snippet (prompt-only heuristic)."
    )

    detections = [
        DemoScanDetection(
            type="jailbreak",
            detected=jail_detected,
            confidence=min(1.0, jail_conf),
            severity=_demo_detection_severity(jail_conf, jail_detected),
            details=jail_details,
            patterns=jail_patterns[:12] if jail_patterns else None,
        ),
        DemoScanDetection(
            type="toxicity",
            detected=tox_detected,
            confidence=min(1.0, tox_score),
            severity=_demo_detection_severity(tox_score, tox_detected),
            details=tox_details,
            patterns=(tox_r.get("categories") or [])[:12] or None,
        ),
        DemoScanDetection(
            type="bias",
            detected=bias_detected,
            confidence=min(1.0, bias_score),
            severity=_demo_detection_severity(bias_score, bias_detected),
            details=bias_details,
            patterns=(bias_r.get("flags") or [])[:12] or None,
        ),
        DemoScanDetection(
            type="hallucination",
            detected=hall_detected,
            confidence=min(1.0, hall_score),
            severity=_demo_detection_severity(hall_score, hall_detected),
            details=hall_details,
            patterns=None,
        ),
    ]

    severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1, "safe": 0}
    overall_severity = "safe"
    for d in detections:
        if severity_order[d.severity] > severity_order[overall_severity]:
            overall_severity = d.severity

    safe = not any(d.detected for d in detections)

    if safe:
        recommendation = "This prompt appears safe to process. No major threats flagged by the ensemble."
    elif overall_severity == "critical":
        recommendation = "BLOCK: Critical risk signals — block or escalate for manual review."
    elif overall_severity == "high":
        recommendation = "BLOCK/REVIEW: High-risk signals — require review or stricter policy."
    elif overall_severity == "medium":
        recommendation = "FLAG: Moderate concerns — monitor or apply guardrails."
    else:
        recommendation = "MONITOR: Low-level signals — proceed with logging if required."

    processing_time_ms = max(1, int((time.perf_counter() - start) * 1000))

    return DemoScanResponse(
        safe=safe,
        overall_severity=overall_severity,  # type: ignore[arg-type]
        detections=detections,
        processing_time_ms=processing_time_ms,
        recommendation=recommendation,
    )


@router.post("/toxicity", response_model=ToxicityResponse)
async def analyze_toxicity(
    request: ToxicityRequest,
    tenant_id: str = Depends(verify_api_key),
    mongodb: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Analyze text for toxicity using custom transformer models.
    
    Uses open-source models instead of OpenAI Moderation API.
    Returns toxicity score, flagged status, and categories.
    """
    # Check credits before processing
    credit_manager = MongoCreditManager(mongodb)
    try:
        await credit_manager.check_credits(tenant_id, operation_type="toxicity")
    except InsufficientCreditsException as e:
        raise HTTPException(
            status_code=402,  # Payment Required
            detail={
                "error": "Insufficient credits",
                "required": e.required,
                "available": e.available,
                "balance": e.balance,
            }
        )
    
    # Use Detoxify detector (fallback to custom if Detoxify fails)
    try:
        result = await toxicity_detector.analyze(request.text)
    except Exception as e:
        print(f"Detoxify failed, falling back to custom detector: {e}")
        result = await custom_toxicity_detector.analyze(request.text)
    
    # Deduct credits after successful processing
    try:
        await credit_manager.deduct_credits(
            tenant_id=tenant_id,
            amount=credit_manager.CREDIT_COSTS["toxicity"],
            operation_type="toxicity",
            reference_type="api_call",
            description="Toxicity analysis",
        )
    except InsufficientCreditsException as e:
        # Should not happen as we checked above, but handle gracefully
        raise HTTPException(
            status_code=402,
            detail={
                "error": "Insufficient credits",
                "required": e.required,
                "available": e.available,
            }
        )
    
    return ToxicityResponse(
        toxicity_score=result["toxicity_score"],
        flagged=result["flagged"],
        categories=result["categories"],
    )


@router.post("/bias", response_model=BiasResponse)
async def analyze_bias(
    request: BiasRequest,
    tenant_id: str = Depends(verify_api_key),
    mongodb: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Analyze text for demographic bias using enhanced detection.
    
    Uses stereotype association, fairness metrics, and demographic parity testing.
    """
    # Check credits before processing
    credit_manager = MongoCreditManager(mongodb)
    await credit_manager.check_credits(tenant_id, operation_type="bias")
    
    result = await enhanced_bias_detector.analyze_comprehensive(
        prompt=request.prompt,
        response=request.response,
        demographic_variants=request.variants,
    )
    
    # Deduct credits after successful processing
    await credit_manager.deduct_credits(
        tenant_id=tenant_id,
        amount=credit_manager.CREDIT_COSTS["bias"],
        operation_type="bias",
        reference_type="api_call",
        description="Bias analysis",
    )
    
    return BiasResponse(
        bias_score=result["bias_score"],
        flags=result["flags"],
        details=result.get("details"),
    )


@router.post("/jailbreak", response_model=JailbreakResponse)
async def detect_jailbreak(
    request: JailbreakRequest,
    tenant_id: str = Depends(verify_api_key),
    mongodb: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Detect jailbreak attempts and prompt injections using advanced detection.
    
    Uses pattern matching, semantic analysis, behavioral indicators, and adversarial detection.
    """
    # Check credits before processing
    credit_manager = MongoCreditManager(mongodb)
    await credit_manager.check_credits(tenant_id, operation_type="jailbreak")
    
    # Get context if available (user history, etc.)
    context = request.__dict__.get("context", None)
    
    result = await advanced_jailbreak_detector.detect(request.text, context)
    
    # Deduct credits after successful processing
    await credit_manager.deduct_credits(
        tenant_id=tenant_id,
        amount=credit_manager.CREDIT_COSTS["jailbreak"],
        operation_type="jailbreak",
        reference_type="api_call",
        description="Jailbreak detection",
    )
    
    return JailbreakResponse(
        jailbreak_flag=result["jailbreak_flag"],
        confidence=result["confidence"],
        patterns_detected=result.get("components", {}).get("patterns_found", []),
    )


@router.post("/hallucination", response_model=HallucinationResponse)
async def detect_hallucination(
    request: HallucinationRequest,
    tenant_id: str = Depends(verify_api_key),
    mongodb: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Detect hallucinations in LLM responses.
    
    Uses semantic consistency, contradiction detection, factuality checking,
    pattern analysis, and confidence calibration.
    """
    # Check credits before processing
    credit_manager = MongoCreditManager(mongodb)
    await credit_manager.check_credits(tenant_id, operation_type="hallucination")
    
    result = await hallucination_detector.detect(
        prompt=request.prompt,
        response=request.response,
        context=request.context,
    )
    
    # Deduct credits after successful processing
    await credit_manager.deduct_credits(
        tenant_id=tenant_id,
        amount=credit_manager.CREDIT_COSTS["hallucination"],
        operation_type="hallucination",
        reference_type="api_call",
        description="Hallucination detection",
    )
    
    return HallucinationResponse(
        hallucination_score=result["hallucination_score"],
        flagged=result["flagged"],
        confidence=result["confidence"],
        recommendation=result["recommendation"],
        components=result.get("components", {}),
    )


@router.post("/explain", response_model=ExplainResponse)
async def explain_issues(
    request: ExplainRequest,
    tenant_id: str = Depends(verify_api_key),
):
    """
    Generate explanation for flagged content.
    
    Now supports:
    - SHAP values for feature importance (toxicity, bias)
    - LIME explanations for local interpretability (hallucination)
    - Token-level importance scores
    - Category-level explanations
    
    Args:
        request: Explanation request with text, issues, and optional SHAP/LIME flags
        tenant_id: Tenant ID from API key
        
    Returns:
        Detailed explanation with SHAP/LIME data
    """
    result = await explainability_engine.explain(
        text=request.text,
        issues=request.issues,
        prompt=request.prompt,
        response=request.response,
        include_shap=request.include_shap,
        include_lime=request.include_lime,
        context=request.context,
    )
    
    return ExplainResponse(
        explanation=result["explanation"],
        highlighted_spans=result["highlighted_spans"],
        shap_values=result.get("shap_values"),
        lime_explanations=result.get("lime_explanations"),
    )


@router.post("/remediate", response_model=RemediateResponse)
async def remediate_content(
    request: RemediateRequest,
    tenant_id: str = Depends(verify_api_key),
):
    """
    Remediate unsafe content.
    
    Returns a safer version of the text while preserving intent.
    """
    result = await remediation_engine.remediate(
        text=request.text,
        issue=request.issue,
    )
    
    return RemediateResponse(
        remediated_text=result["remediated_text"],
        original_score=result["original_score"],
        new_score=result["new_score"],
        changes_made=result["changes_made"],
    )


@router.post("/custom-classify")
async def custom_classify(
    request: dict,
    tenant_id: str = Depends(verify_api_key),
):
    """
    Run custom classifiers (PII, misinformation, compliance, etc.).
    
    Goes beyond standard toxicity to detect:
    - PII (email, phone, SSN, credit cards)
    - Misinformation patterns
    - Unprofessional content
    - Compliance violations (HIPAA, GDPR)
    """
    text = request.get("text", "")
    enabled_classifiers = request.get("classifiers", None)
    
    result = await classifier_registry.classify_all(text, enabled_classifiers)
    
    return {
        "overall_score": result["overall_score"],
        "flagged": result["flagged"],
        "results": result["classifier_results"],
        "available_classifiers": classifier_registry.list_classifiers(),
    }


@router.post("/policy-check")
async def check_policy(
    request: dict,
    tenant_id: str = Depends(verify_api_key),
):
    """
    Check text against tenant-specific policy rules.
    
    Supports custom rules for:
    - Industry-specific compliance (HIPAA, SEC, FINRA)
    - Corporate communication standards
    - Domain-specific keywords/patterns
    - Confidential information detection
    """
    text = request.get("text", "")
    
    result = policy_engine.evaluate_policy(tenant_id, text)
    
    return result


@router.post("/advanced-bias-test")
async def advanced_bias_test(
    request: dict,
    tenant_id: str = Depends(verify_api_key),
):
    """
    Run comprehensive paired demographic bias testing.
    
    Tests actual LLM responses across:
    - Gender variants (he/she/they)
    - Race/ethnicity variants
    - Age variants
    - Professional context pronoun usage
    
    Returns detailed bias analysis with variance scores.
    """
    base_prompt = request.get("prompt", "")
    test_demographics = request.get("demographics", ["gender"])
    model = request.get("model", "gpt-3.5-turbo")
    
    result = await bias_test_suite.run_comprehensive_bias_tests(
        base_prompt,
        test_demographics,
        model,
    )
    
    return result


@router.get("/classifiers")
async def list_classifiers(
    tenant_id: str = Depends(verify_api_key),
):
    """
    List all available custom classifiers.
    
    Returns:
        - PII detector
        - Misinformation detector
        - Professional context classifier
        - Compliance classifier
        - Any custom tenant classifiers
    """
    return {
        "classifiers": classifier_registry.list_classifiers(),
        "description": {
            "pii_detector": "Detects personally identifiable information (email, phone, SSN, etc.)",
            "misinfo_detector": "Detects misinformation patterns and claims",
            "professional_context": "Flags unprofessional language in business contexts",
            "compliance": "Detects compliance-sensitive content (HIPAA, legal, financial)",
        },
    }


@router.get("/policy/{tenant_id}")
async def get_tenant_policy(
    tenant_id: str,
    auth_tenant_id: str = Depends(verify_api_key),
):
    """
    Get tenant's custom policy configuration.
    
    Returns configured rules, thresholds, and enabled features.
    """
    # Verify tenant access
    if tenant_id != auth_tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant's policy")
    
    policy = policy_engine.get_policy(tenant_id)
    
    if not policy:
        return {
            "message": "No custom policy configured",
            "default_policy": True,
        }
    
    return {
        "tenant_id": policy.tenant_id,
        "name": policy.name,
        "description": policy.description,
        "enabled": policy.enabled,
        "rules": [
            {
                "id": rule.id,
                "name": rule.name,
                "description": rule.description,
                "action": rule.action,
                "severity": rule.severity,
                "enabled": rule.enabled,
            }
            for rule in policy.rules
        ],
        "thresholds": {
            "toxicity": policy.toxicity_threshold,
            "bias": policy.bias_threshold,
            "pii": policy.pii_threshold,
        },
        "features": {
            "toxicity": policy.enable_toxicity,
            "bias": policy.enable_bias,
            "jailbreak": policy.enable_jailbreak,
            "pii": policy.enable_pii,
            "custom_classifiers": policy.enable_custom_classifiers,
        },
    }
