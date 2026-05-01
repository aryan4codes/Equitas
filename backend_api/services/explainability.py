"""
Explainability service for safety violations.
Enhanced with SHAP and LIME for detailed explanations.
"""

import re
from typing import Dict, Any, List, Optional

from .shap_toxicity import get_toxicity_shap_explainer
from .shap_bias import get_bias_shap_explainer
from .lime_hallucination import get_hallucination_lime_explainer
from .detoxify_toxicity import get_detoxify_detector


class ExplainabilityEngine:
    """Generates explanations for flagged content with SHAP/LIME support."""
    
    def __init__(self):
        """Initialize explainability engine with SHAP/LIME explainers."""
        self.toxicity_detector = get_detoxify_detector(model_name="original")
        self.toxicity_shap_explainer = get_toxicity_shap_explainer(self.toxicity_detector)
        self.bias_shap_explainer = get_bias_shap_explainer()
    
    async def explain(
        self,
        text: str,
        issues: List[str],
        prompt: Optional[str] = None,
        response: Optional[str] = None,
        include_shap: bool = True,
        include_lime: bool = True,
        context: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Generate explanation for flagged content.
        
        Args:
            text: The flagged text
            issues: List of issues (e.g., ["toxicity", "bias"])
            prompt: Optional prompt (for bias/hallucination)
            response: Optional response (for bias/hallucination)
            include_shap: Whether to include SHAP values
            include_lime: Whether to include LIME explanations
            context: Optional context for hallucination detection
            
        Returns:
            Dict with explanation, highlighted_spans, and SHAP/LIME data
        """
        explanations = []
        highlighted_spans = []
        shap_data = {}
        lime_data = {}
        
        for issue in issues:
            if issue == "toxicity":
                result = await self._explain_toxicity(text, include_shap)
                explanations.append(result["explanation"])
                highlighted_spans.extend(result.get("spans", []))
                if include_shap and result.get("shap_data"):
                    shap_data["toxicity"] = result["shap_data"]
            
            elif issue == "bias":
                if prompt and response:
                    result = await self._explain_bias(
                        prompt, response, text, include_shap
                    )
                    explanations.append(result["explanation"])
                    highlighted_spans.extend(result.get("spans", []))
                    if include_shap and result.get("shap_data"):
                        shap_data["bias"] = result["shap_data"]
                else:
                    # Fallback to basic explanation
                    result = self._explain_bias_basic(text)
                    explanations.append(result["explanation"])
                    highlighted_spans.extend(result.get("spans", []))
            
            elif issue == "jailbreak":
                result = self._explain_jailbreak(text)
                explanations.append(result["explanation"])
                highlighted_spans.extend(result.get("spans", []))
            
            elif issue == "hallucination":
                if prompt and response:
                    result = await self._explain_hallucination(
                        prompt, response, context, include_lime
                    )
                    explanations.append(result["explanation"])
                    highlighted_spans.extend(result.get("spans", []))
                    if include_lime and result.get("lime_data"):
                        lime_data["hallucination"] = result["lime_data"]
        
        full_explanation = " ".join(explanations)
        
        response_data = {
            "explanation": full_explanation,
            "highlighted_spans": highlighted_spans,
        }
        
        if shap_data:
            response_data["shap_values"] = shap_data
        if lime_data:
            response_data["lime_explanations"] = lime_data
        
        return response_data
    
    async def _explain_toxicity(
        self, text: str, include_shap: bool = True
    ) -> Dict[str, Any]:
        """Explain toxicity issues with optional SHAP."""
        result = {
            "explanation": "",
            "spans": [],
            "shap_data": None,
        }
        
        # Get SHAP explanation if available
        if include_shap and self.toxicity_shap_explainer:
            try:
                shap_result = self.toxicity_shap_explainer.explain(text)
                result["shap_data"] = shap_result
                result["explanation"] = shap_result.get("explanation_summary", "")
                
                # Create highlighted spans from SHAP tokens
                for token_info in shap_result.get("tokens", []):
                    if token_info.get("impact") in ["high", "medium"]:
                        # Find token position in text
                        token = token_info["token"]
                        start = text.find(token)
                        if start >= 0:
                            result["spans"].append({
                                "start": start,
                                "end": start + len(token),
                                "text": token,
                                "issue": "toxic_language",
                                "shap_value": token_info["shap_value"],
                                "impact": token_info["impact"],
                            })
            except Exception as e:
                print(f"SHAP explanation failed: {e}")
                # Fallback to basic
                result.update(self._explain_toxicity_basic(text))
        else:
            result.update(self._explain_toxicity_basic(text))
        
        return result
    
    def _explain_toxicity_basic(self, text: str) -> Dict[str, Any]:
        """Basic toxicity explanation (fallback)."""
        toxic_words = [
            "hate", "stupid", "idiot", "dumb", "kill", "die",
            "fuck", "shit", "damn", "bitch", "asshole"
        ]
        
        spans = []
        found_words = []
        
        for word in toxic_words:
            pattern = r'\b' + re.escape(word) + r'\b'
            for match in re.finditer(pattern, text, re.IGNORECASE):
                spans.append({
                    "start": match.start(),
                    "end": match.end(),
                    "text": match.group(),
                    "issue": "toxic_language"
                })
                found_words.append(match.group())
        
        if found_words:
            explanation = f"The following terms triggered toxicity detection: {', '.join(set(found_words))}. These words may be offensive or harmful."
        else:
            explanation = "This content contains toxic or harmful language."
        
        return {
            "explanation": explanation,
            "spans": spans,
        }
    
    async def _explain_bias(
        self,
        prompt: str,
        response: str,
        text: str,
        include_shap: bool = True,
    ) -> Dict[str, Any]:
        """Explain bias issues with optional SHAP."""
        result = {
            "explanation": "",
            "spans": [],
            "shap_data": None,
        }
        
        if include_shap and self.bias_shap_explainer:
            try:
                # Get demographic variants from enhanced bias detector
                from .enhanced_bias import get_bias_detector
                bias_detector = get_bias_detector()
                bias_result = await bias_detector.analyze_comprehensive(
                    prompt=prompt,
                    response=response,
                    demographic_variants=None,
                )
                
                # Generate SHAP explanation
                shap_result = self.bias_shap_explainer.explain_feature_importance(
                    prompt, response, bias_result.get("bias_score", 0.0)
                )
                
                result["shap_data"] = shap_result
                result["explanation"] = shap_result.get("summary", "")
            except Exception as e:
                print(f"Bias SHAP explanation failed: {e}")
                result.update(self._explain_bias_basic(text))
        else:
            result.update(self._explain_bias_basic(text))
        
        return result
    
    def _explain_bias_basic(self, text: str) -> Dict[str, Any]:
        """Basic bias explanation (fallback)."""
        bias_patterns = {
            r'(female|woman) (doctor|engineer|CEO)': "gendered professional qualifier",
            r'(old people|elderly) can\'?t': "age-based assumption",
            r'women are (bad at|not good at)': "gender stereotype",
        }
        
        spans = []
        issues_found = []
        
        for pattern, issue_type in bias_patterns.items():
            for match in re.finditer(pattern, text, re.IGNORECASE):
                spans.append({
                    "start": match.start(),
                    "end": match.end(),
                    "text": match.group(),
                    "issue": issue_type
                })
                issues_found.append(issue_type)
        
        if issues_found:
            explanation = f"Detected potential bias: {', '.join(set(issues_found))}."
        else:
            explanation = "This content may contain demographic bias or stereotypes."
        
        return {
            "explanation": explanation,
            "spans": spans,
        }
    
    async def _explain_hallucination(
        self,
        prompt: str,
        response: str,
        context: Optional[List[str]],
        include_lime: bool = True,
    ) -> Dict[str, Any]:
        """Explain hallucination with optional LIME."""
        result = {
            "explanation": "",
            "spans": [],
            "lime_data": None,
        }
        
        if include_lime:
            try:
                from .hallucination import get_hallucination_detector
                from .lime_hallucination import get_hallucination_lime_explainer
                
                hallucination_detector = get_hallucination_detector()
                lime_explainer = get_hallucination_lime_explainer(hallucination_detector)
                
                lime_result = lime_explainer.explain(prompt, response, context)
                result["lime_data"] = lime_result
                result["explanation"] = lime_result.get("overall_explanation", "")
                
                # Create spans from high-impact sentences
                for sentence_info in lime_result.get("sentences", []):
                    if sentence_info.get("impact_level") == "high":
                        sentence = sentence_info["sentence"]
                        start = response.find(sentence)
                        if start >= 0:
                            result["spans"].append({
                                "start": start,
                                "end": start + len(sentence),
                                "text": sentence,
                                "issue": "hallucination",
                                "impact": sentence_info["impact"],
                            })
            except Exception as e:
                print(f"LIME explanation failed: {e}")
                result["explanation"] = "Unable to generate detailed hallucination explanation."
        else:
            result["explanation"] = "Response may contain unsupported or inaccurate claims."
        
        return result
    
    def _explain_jailbreak(self, text: str) -> Dict[str, Any]:
        """Explain jailbreak attempts."""
        jailbreak_patterns = {
            r'ignore (previous|all previous)': "attempt to override instructions",
            r'forget (everything|all)': "attempt to reset context",
            r'you are now': "roleplay injection",
            r'DAN mode': "known jailbreak technique",
        }
        
        spans = []
        techniques = []
        
        for pattern, technique in jailbreak_patterns.items():
            for match in re.finditer(pattern, text, re.IGNORECASE):
                spans.append({
                    "start": match.start(),
                    "end": match.end(),
                    "text": match.group(),
                    "issue": technique
                })
                techniques.append(technique)
        
        if techniques:
            explanation = f"Detected jailbreak attempt: {', '.join(set(techniques))}."
        else:
            explanation = "This content contains patterns associated with prompt injection or jailbreak attempts."
        
        return {
            "explanation": explanation,
            "spans": spans,
        }
