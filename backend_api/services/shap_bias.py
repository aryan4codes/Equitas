"""
SHAP explainer for bias detection.
Provides detailed explanations of demographic bias and fairness violations.
"""

import numpy as np
from typing import Dict, Any, List, Optional
import shap
from sentence_transformers import SentenceTransformer
import torch

from ..core.config import get_settings

settings = get_settings()


class BiasSHAPExplainer:
    """
    SHAP explainer for bias detection.
    
    Provides explanations for:
    - Demographic variant impact (gender, race, age)
    - Feature importance in prompt/response
    - Fairness violation quantification
    """
    
    def __init__(self):
        """Initialize SHAP explainer for bias detection."""
        try:
            # Use sentence transformer for text embeddings
            self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
            self.explainer: Optional[shap.Explainer] = None
        except Exception as e:
            print(f"Failed to initialize bias SHAP explainer: {e}")
            self.embedder = None
    
    def explain_demographic_bias(
        self,
        base_prompt: str,
        response: str,
        demographic_variants: Dict[str, List[str]],
        variant_scores: Dict[str, float],
    ) -> Dict[str, Any]:
        """
        Explain demographic bias using SHAP.
        
        Args:
            base_prompt: Original prompt
            response: LLM response
            demographic_variants: Dict mapping demographics to variants
                e.g., {"gender": ["male", "female", "non-binary"]}
            variant_scores: Dict mapping variant to bias score
                e.g., {"male": 0.1, "female": 0.5}
        
        Returns:
            Dict with SHAP values for each demographic variant
        """
        if not self.embedder:
            return self._fallback_explanation(demographic_variants, variant_scores)
        
        try:
            demographic_impact = {}
            
            # Calculate SHAP values for each demographic dimension
            for demographic, variants in demographic_variants.items():
                if len(variants) < 2:
                    continue
                
                # Get scores for each variant
                variant_scores_list = [
                    variant_scores.get(variant, 0.0) for variant in variants
                ]
                
                # Calculate variance and impact
                variance = np.var(variant_scores_list)
                mean_score = np.mean(variant_scores_list)
                
                # Calculate SHAP-like values (difference from mean)
                variant_shap = {}
                for variant in variants:
                    score = variant_scores.get(variant, mean_score)
                    shap_value = score - mean_score
                    
                    variant_shap[variant] = {
                        "shap_value": float(shap_value),
                        "score": float(score),
                        "impact": (
                            "high" if abs(shap_value) > 0.2
                            else "medium" if abs(shap_value) > 0.1
                            else "low"
                        ),
                        "direction": "biased_against" if shap_value > 0 else "biased_toward",
                    }
                
                # Identify most biased variant
                most_biased = max(
                    variant_shap.items(),
                    key=lambda x: abs(x[1]["shap_value"])
                )
                
                demographic_impact[demographic] = {
                    "variants": variant_shap,
                    "variance": float(variance),
                    "mean_score": float(mean_score),
                    "most_biased_variant": most_biased[0],
                    "bias_magnitude": abs(most_biased[1]["shap_value"]),
                    "explanation": self._explain_demographic_bias(
                        demographic, variant_shap, variance
                    ),
                }
            
            # Calculate overall bias explanation
            overall_explanation = self._generate_overall_explanation(demographic_impact)
            
            return {
                "demographic_impact": demographic_impact,
                "overall_explanation": overall_explanation,
                "bias_summary": self._generate_bias_summary(demographic_impact),
            }
        except Exception as e:
            print(f"Bias SHAP explanation failed: {e}")
            return self._fallback_explanation(demographic_variants, variant_scores)
    
    def explain_feature_importance(
        self, prompt: str, response: str, bias_score: float
    ) -> Dict[str, Any]:
        """
        Explain which features in prompt/response contribute to bias.
        
        Args:
            prompt: Original prompt
            response: LLM response
            bias_score: Overall bias score
        
        Returns:
            Dict with feature importance for prompt and response
        """
        if not self.embedder:
            return {"prompt_features": [], "response_features": []}
        
        try:
            # Tokenize prompt and response
            prompt_tokens = prompt.split()
            response_tokens = response.split()
            
            # Calculate feature importance using perturbation
            prompt_features = self._calculate_token_importance(
                prompt, prompt_tokens, "prompt"
            )
            response_features = self._calculate_token_importance(
                response, response_tokens, "response"
            )
            
            return {
                "prompt_features": sorted(
                    prompt_features,
                    key=lambda x: abs(x["importance"]),
                    reverse=True
                )[:10],
                "response_features": sorted(
                    response_features,
                    key=lambda x: abs(x["importance"]),
                    reverse=True
                )[:10],
                "summary": self._generate_feature_summary(
                    prompt_features, response_features
                ),
            }
        except Exception as e:
            print(f"Feature importance calculation failed: {e}")
            return {"prompt_features": [], "response_features": []}
    
    def _calculate_token_importance(
        self, text: str, tokens: List[str], text_type: str
    ) -> List[Dict[str, Any]]:
        """Calculate importance of each token using perturbation."""
        try:
            # Get baseline embedding
            baseline_embedding = self.embedder.encode(text, convert_to_numpy=True)
            
            token_importance = []
            for token in tokens:
                # Remove token and measure change
                text_without = text.replace(token, "", 1).strip()
                if not text_without:
                    continue
                
                modified_embedding = self.embedder.encode(
                    text_without, convert_to_numpy=True
                )
                
                # Calculate cosine distance change
                from sklearn.metrics.pairwise import cosine_similarity
                distance = cosine_similarity(
                    [baseline_embedding], [modified_embedding]
                )[0][0]
                
                importance = 1.0 - distance
                
                token_importance.append({
                    "token": token,
                    "importance": float(importance),
                    "impact": (
                        "high" if importance > 0.1
                        else "medium" if importance > 0.05
                        else "low"
                    ),
                })
            
            return token_importance
        except Exception:
            return []
    
    def _explain_demographic_bias(
        self,
        demographic: str,
        variant_shap: Dict[str, Dict[str, Any]],
        variance: float,
    ) -> str:
        """Generate explanation for demographic bias."""
        if variance < 0.01:
            return f"No significant bias detected across {demographic} variants."
        
        # Find most and least biased variants
        sorted_variants = sorted(
            variant_shap.items(),
            key=lambda x: abs(x[1]["shap_value"]),
            reverse=True
        )
        
        most_biased = sorted_variants[0]
        least_biased = sorted_variants[-1]
        
        if most_biased[1]["shap_value"] > 0:
            return (
                f"Model shows bias against {most_biased[0]} "
                f"(score: {most_biased[1]['score']:.2f}) compared to "
                f"{least_biased[0]} (score: {least_biased[1]['score']:.2f}). "
                f"Variance: {variance:.3f}"
            )
        else:
            return (
                f"Model shows bias toward {most_biased[0]} "
                f"(score: {most_biased[1]['score']:.2f}) compared to "
                f"{least_biased[0]} (score: {least_biased[1]['score']:.2f}). "
                f"Variance: {variance:.3f}"
            )
    
    def _generate_overall_explanation(
        self, demographic_impact: Dict[str, Any]
    ) -> str:
        """Generate overall bias explanation."""
        if not demographic_impact:
            return "No demographic bias detected."
        
        # Find most biased demographic
        most_biased_demo = max(
            demographic_impact.items(),
            key=lambda x: x[1]["bias_magnitude"]
        )
        
        return (
            f"Detected bias across {len(demographic_impact)} demographic dimensions. "
            f"Most significant bias in {most_biased_demo[0]} "
            f"(magnitude: {most_biased_demo[1]['bias_magnitude']:.2f})."
        )
    
    def _generate_bias_summary(self, demographic_impact: Dict[str, Any]) -> str:
        """Generate concise bias summary."""
        summaries = []
        
        for demographic, impact in demographic_impact.items():
            most_biased = impact["most_biased_variant"]
            magnitude = impact["bias_magnitude"]
            
            if magnitude > 0.2:
                summaries.append(
                    f"{demographic}: bias against {most_biased} "
                    f"(magnitude: {magnitude:.2f})"
                )
        
        if summaries:
            return "; ".join(summaries)
        return "No significant bias detected."
    
    def _generate_feature_summary(
        self,
        prompt_features: List[Dict[str, Any]],
        response_features: List[Dict[str, Any]],
    ) -> str:
        """Generate feature importance summary."""
        top_prompt = [
            f["token"] for f in prompt_features[:3] if f["impact"] in ["high", "medium"]
        ]
        top_response = [
            f["token"] for f in response_features[:3] if f["impact"] in ["high", "medium"]
        ]
        
        parts = []
        if top_prompt:
            parts.append(f"Prompt features: {', '.join(top_prompt)}")
        if top_response:
            parts.append(f"Response features: {', '.join(top_response)}")
        
        return ". ".join(parts) if parts else "No significant features identified."
    
    def _fallback_explanation(
        self,
        demographic_variants: Dict[str, List[str]],
        variant_scores: Dict[str, float],
    ) -> Dict[str, Any]:
        """Fallback explanation when SHAP fails."""
        return {
            "demographic_impact": {},
            "overall_explanation": "SHAP explanation unavailable.",
            "bias_summary": "Unable to generate detailed bias explanation.",
            "error": "SHAP explainer not initialized",
        }


# Global explainer instance
_bias_shap_explainer: Optional[BiasSHAPExplainer] = None


def get_bias_shap_explainer() -> BiasSHAPExplainer:
    """Get or create global bias SHAP explainer instance."""
    global _bias_shap_explainer
    if _bias_shap_explainer is None:
        _bias_shap_explainer = BiasSHAPExplainer()
    return _bias_shap_explainer

