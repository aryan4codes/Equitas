"""
Analysis API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.auth import verify_api_key
from ...models.schemas import (
    ToxicityRequest, ToxicityResponse,
    BiasRequest, BiasResponse,
    JailbreakRequest, JailbreakResponse,
    ExplainRequest, ExplainResponse,
    RemediateRequest, RemediateResponse,
)
from ...services.toxicity import ToxicityDetector
from ...services.bias import BiasDetector
from ...services.jailbreak import JailbreakDetector
from ...services.explainability import ExplainabilityEngine
from ...services.remediation import RemediationEngine
from ...services.custom_classifiers import classifier_registry
from ...services.policy_engine import policy_engine
from ...services.advanced_bias import bias_test_suite

router = APIRouter()

# Initialize services
toxicity_detector = ToxicityDetector()
bias_detector = BiasDetector()
jailbreak_detector = JailbreakDetector()
explainability_engine = ExplainabilityEngine()
remediation_engine = RemediationEngine()


@router.post("/toxicity", response_model=ToxicityResponse)
async def analyze_toxicity(
    request: ToxicityRequest,
    tenant_id: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Analyze text for toxicity using OpenAI Moderation API.
    
    Returns toxicity score, flagged status, and categories.
    """
    result = await toxicity_detector.analyze(request.text)
    
    return ToxicityResponse(
        toxicity_score=result["toxicity_score"],
        flagged=result["flagged"],
        categories=result["categories"],
    )


@router.post("/bias", response_model=BiasResponse)
async def analyze_bias(
    request: BiasRequest,
    tenant_id: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Analyze text for demographic bias.
    
    Uses paired prompt testing and pattern matching.
    """
    result = await bias_detector.analyze(
        prompt=request.prompt,
        response=request.response,
        variants=request.variants,
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
    db: AsyncSession = Depends(get_db),
):
    """
    Detect jailbreak attempts and prompt injections.
    
    Scans for known jailbreak patterns.
    """
    result = await jailbreak_detector.detect(request.text)
    
    return JailbreakResponse(
        jailbreak_flag=result["jailbreak_flag"],
        confidence=result["confidence"],
        patterns_detected=result["patterns_detected"],
    )


@router.post("/explain", response_model=ExplainResponse)
async def explain_issues(
    request: ExplainRequest,
    tenant_id: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate explanation for flagged content.
    
    Highlights problematic spans and provides rationale.
    """
    result = await explainability_engine.explain(
        text=request.text,
        issues=request.issues,
    )
    
    return ExplainResponse(
        explanation=result["explanation"],
        highlighted_spans=result["highlighted_spans"],
    )


@router.post("/remediate", response_model=RemediateResponse)
async def remediate_content(
    request: RemediateRequest,
    tenant_id: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
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
