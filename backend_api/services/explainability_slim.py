"""
Lightweight explanations when EQUITAS_SLIM=1 (no PyTorch / SHAP / LIME).

Mirrors the basic fallback paths in ExplainabilityEngine without heavy imports.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


def _explain_toxicity_basic(text: str) -> Dict[str, Any]:
    toxic_words = [
        "hate",
        "stupid",
        "idiot",
        "dumb",
        "kill",
        "die",
        "fuck",
        "shit",
        "damn",
        "bitch",
        "asshole",
        
    ]

    spans: List[Dict[str, Any]] = []
    found_words: List[str] = []

    for word in toxic_words:
        pattern = r"\b" + re.escape(word) + r"\b"
        for match in re.finditer(pattern, text, re.IGNORECASE):
            spans.append(
                {
                    "start": match.start(),
                    "end": match.end(),
                    "text": match.group(),
                    "issue": "toxic_language",
                }
            )
            found_words.append(match.group())

    if found_words:
        explanation = (
            f"The following terms triggered toxicity detection: {', '.join(set(found_words))}. "
            "These words may be offensive or harmful."
        )
    else:
        explanation = "This content contains toxic or harmful language."

    return {"explanation": explanation, "spans": spans}


def _explain_bias_basic(text: str) -> Dict[str, Any]:
    bias_patterns = {
        r"(female|woman) (doctor|engineer|CEO)": "gendered professional qualifier",
        r"(old people|elderly) can'?t": "age-based assumption",
        r"women are (bad at|not good at)": "gender stereotype",
    }

    spans: List[Dict[str, Any]] = []
    issues_found: List[str] = []

    for pattern, issue_type in bias_patterns.items():
        for match in re.finditer(pattern, text, re.IGNORECASE):
            spans.append(
                {
                    "start": match.start(),
                    "end": match.end(),
                    "text": match.group(),
                    "issue": issue_type,
                }
            )
            issues_found.append(issue_type)

    if issues_found:
        explanation = f"Detected potential bias: {', '.join(set(issues_found))}."
    else:
        explanation = "This content may contain demographic bias or stereotypes."

    return {"explanation": explanation, "spans": spans}


def _explain_jailbreak(text: str) -> Dict[str, Any]:
    jailbreak_patterns = {
        r"ignore (previous|all previous)": "attempt to override instructions",
        r"forget (everything|all)": "attempt to reset context",
        r"you are now": "roleplay injection",
        r"DAN mode": "known jailbreak technique",
    }

    spans: List[Dict[str, Any]] = []
    techniques: List[str] = []

    for pattern, technique in jailbreak_patterns.items():
        for match in re.finditer(pattern, text, re.IGNORECASE):
            spans.append(
                {
                    "start": match.start(),
                    "end": match.end(),
                    "text": match.group(),
                    "issue": technique,
                }
            )
            techniques.append(technique)

    if techniques:
        explanation = f"Detected jailbreak attempt: {', '.join(set(techniques))}."
    else:
        explanation = (
            "This content contains patterns associated with prompt injection "
            "or jailbreak attempts."
        )

    return {"explanation": explanation, "spans": spans}


def explain_without_ml(
    text: str,
    issues: List[str],
    prompt: Optional[str] = None,
    response: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Produce explanation + spans without SHAP/LIME.

    Same keys as ExplainabilityEngine.explain for API compatibility (no shap_values / lime).
    """
    explanations: List[str] = []
    highlighted_spans: List[Dict[str, Any]] = []

    for issue in issues:
        if issue == "toxicity":
            r = _explain_toxicity_basic(text)
            explanations.append(r["explanation"])
            highlighted_spans.extend(r.get("spans", []))

        elif issue == "bias":
            bias_text = text
            if prompt is not None and response is not None:
                bias_text = response
            r = _explain_bias_basic(bias_text)
            explanations.append(r["explanation"])
            highlighted_spans.extend(r.get("spans", []))

        elif issue == "jailbreak":
            r = _explain_jailbreak(text)
            explanations.append(r["explanation"])
            highlighted_spans.extend(r.get("spans", []))

        elif issue == "hallucination":
            explanations.append(
                "Response may contain unsupported or inaccurate claims relative to the prompt."
            )

    full_explanation = " ".join(explanations) if explanations else "Safety checks flagged this content."

    return {
        "explanation": full_explanation,
        "highlighted_spans": highlighted_spans,
    }
