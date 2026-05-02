"""
Lazy detector wiring. Use EQUITAS_SLIM=1 on low-memory hosts (e.g. Render 512MB) to avoid
loading PyTorch / Detoxify / sentence-transformers at startup.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..core.config import get_settings

_toxicity = None
_custom_toxicity = None
_bias = None
_jailbreak = None
_hallucination = None
_legacy_toxicity = None
_explainability = None
_remediation = None


def get_toxicity_analyzer():
    global _toxicity
    if _toxicity is None:
        if get_settings().equitas_slim:
            from .toxicity import ToxicityDetector

            _toxicity = ToxicityDetector()
        else:
            from .detoxify_toxicity import get_detoxify_detector

            _toxicity = get_detoxify_detector(model_name="original")
    return _toxicity


def get_custom_toxicity_analyzer():
    """Heavy HF model; unavailable in slim mode."""
    global _custom_toxicity
    if get_settings().equitas_slim:
        return None
    if _custom_toxicity is None:
        from .custom_toxicity import get_toxicity_detector

        _custom_toxicity = get_toxicity_detector()
    return _custom_toxicity


def get_legacy_toxicity_analyzer():
    global _legacy_toxicity
    if _legacy_toxicity is None:
        from .toxicity import ToxicityDetector

        _legacy_toxicity = ToxicityDetector()
    return _legacy_toxicity


class _BiasSlimAdapter:
    """Expose analyze_comprehensive(...) using lightweight BiasDetector."""

    def __init__(self, inner: Any) -> None:
        self._inner = inner

    async def analyze_comprehensive(
        self,
        prompt: str,
        response: str,
        demographic_variants: Any = None,
    ) -> Dict[str, Any]:
        variants = None
        if demographic_variants and all(isinstance(x, str) for x in demographic_variants):
            variants = demographic_variants
        r = await self._inner.analyze(prompt, response, variants)
        bs = float(r.get("bias_score", 0.0))
        flags = r.get("flags") or []
        return {
            "bias_score": bs,
            "bias_detected": bs > 0.5 or len(flags) > 0,
            "flags": flags,
            "details": r.get("details"),
            "recommendations": [],
        }


def get_bias_analyzer():
    global _bias
    if _bias is None:
        if get_settings().equitas_slim:
            from .bias import BiasDetector

            _bias = _BiasSlimAdapter(BiasDetector())
        else:
            from .enhanced_bias import get_bias_detector

            _bias = get_bias_detector()
    return _bias


def get_jailbreak_analyzer():
    global _jailbreak
    if _jailbreak is None:
        if get_settings().equitas_slim:
            from .jailbreak import JailbreakDetector

            _jailbreak = _JailbreakSlimAdapter(JailbreakDetector())
        else:
            from .advanced_jailbreak import get_jailbreak_detector

            _jailbreak = get_jailbreak_detector()
    return _jailbreak


class _JailbreakSlimAdapter:
    """Map legacy jailbreak output to advanced detector shape."""

    def __init__(self, inner: Any) -> None:
        self._inner = inner

    async def detect(self, text: str, context: Any = None) -> Dict[str, Any]:
        r = await self._inner.detect(text)
        pats = r.get("patterns_detected") or []
        flagged = bool(r.get("jailbreak_flag", False))
        return {
            "jailbreak_flag": flagged,
            "confidence": float(r.get("confidence", 0.0)),
            "components": {"patterns_found": [p[:120] for p in pats]},
            "explanation": (
                "Pattern-based jailbreak / injection heuristics (slim mode)."
                if flagged
                else "No jailbreak patterns matched (slim mode)."
            ),
        }


class _SlimHallucinationDetector:
    """No neural models — length / punctuation heuristic only."""

    async def detect(
        self,
        prompt: str,
        response: str,
        context: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        text = f"{prompt or ''}\n{response or ''}"
        n = len(text)
        q = text.count("?")
        score = min(0.45, 0.08 + (n / 6000) * 0.25 + min(q, 4) * 0.03)
        return {
            "hallucination_score": float(score),
            "flagged": score > 0.32,
            "confidence": float(max(0.0, 1.0 - score)),
            "components": {"slim_mode": True},
            "recommendation": "safe" if score <= 0.32 else "low_risk",
        }


def get_hallucination_analyzer():
    global _hallucination
    if _hallucination is None:
        if get_settings().equitas_slim:
            _hallucination = _SlimHallucinationDetector()
        else:
            from .hallucination import get_hallucination_detector

            _hallucination = get_hallucination_detector()
    return _hallucination


def get_explainability_engine():
    """Returns None in slim mode (SHAP/LIME require heavy models)."""
    global _explainability
    if get_settings().equitas_slim:
        return None
    if _explainability is None:
        from .explainability import ExplainabilityEngine

        _explainability = ExplainabilityEngine()
    return _explainability


def get_remediation_engine():
    global _remediation
    if _remediation is None:
        from .remediation import RemediationEngine

        _remediation = RemediationEngine()
    return _remediation
