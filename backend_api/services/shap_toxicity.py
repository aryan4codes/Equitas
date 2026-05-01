"""
SHAP explainer for toxicity detection.
Provides detailed feature importance and token-level explanations.
"""

import numpy as np
from typing import Dict, Any, List, Optional, Union, TYPE_CHECKING
import re
from detoxify import Detoxify

from ..core.config import get_settings

if TYPE_CHECKING:
    from .detoxify_toxicity import DetoxifyToxicityDetector

settings = get_settings()


class ToxicitySHAPExplainer:
    """
    SHAP explainer for toxicity detection models.
    
    Provides token-level and category-level feature importance
    for understanding why content was flagged as toxic.
    """
    
    def __init__(self, model: Union[Detoxify, "DetoxifyToxicityDetector"]):
        """
        Initialize SHAP explainer for toxicity model.
        
        Args:
            model: Detoxify instance or DetoxifyToxicityDetector (must expose .predict(text))
        """
        self.model = model
        self.explainer: Optional[str] = None  # "perturbation_method" or None
        self.background_data: Optional[List[str]] = None
        self._initialize_explainer()
    
    def _initialize_explainer(self):
        """Initialize SHAP explainer with background data."""
        # For text models, we use a perturbation-based approach instead of KernelExplainer
        # This is more suitable for text and doesn't require background data format conversion
        self.background_data = [
            "This is a normal sentence.",
            "Hello, how are you?",
            "Thank you for your help.",
            "I appreciate your assistance.",
            "Have a great day!",
        ]
        # Mark as initialized (we use perturbation method, not KernelExplainer)
        self.explainer = "perturbation_method"
    
    def explain(self, text: str) -> Dict[str, Any]:
        """
        Generate SHAP explanation for text using perturbation-based method.
        
        Args:
            text: Text to explain
            
        Returns:
            Dict with SHAP values, token importance, and explanations
        """
        if not self.explainer:
            return self._fallback_explanation(text)
        
        try:
            # Calculate base value (expected value) from background data
            base_value = self._calculate_base_value()
            
            # Tokenize text for token-level analysis
            tokens = text.split()
            
            # Calculate per-token SHAP values using perturbation method
            # This is more accurate and faster than KernelExplainer for text
            token_shap_values = self._calculate_token_shap_values(text, tokens)
            
            # Get category-level explanations
            category_explanations = self._get_category_explanations(text)
            
            # Get feature importance ranking
            feature_importance = sorted(
                token_shap_values,
                key=lambda x: abs(x["shap_value"]),
                reverse=True
            )
            
            # Calculate total SHAP value
            total_shap_value = sum(abs(t["shap_value"]) for t in token_shap_values)
            
            return {
                "base_value": base_value,
                "tokens": token_shap_values,
                "feature_importance": feature_importance[:10],  # Top 10
                "category_explanations": category_explanations,
                "total_shap_value": float(total_shap_value),
                "explanation_summary": self._generate_summary(
                    feature_importance, category_explanations
                ),
            }
        except Exception as e:
            print(f"SHAP explanation failed: {e}")
            import traceback
            traceback.print_exc()
            return self._fallback_explanation(text)
    
    def _calculate_base_value(self) -> float:
        """Calculate base value (expected value) from background data."""
        try:
            scores = []
            for bg_text in self.background_data:
                result = self.model.predict(bg_text)
                scores.append(max(result.values()))
            return float(np.mean(scores)) if scores else 0.0
        except Exception:
            return 0.0
    
    def _calculate_token_shap_values(
        self, text: str, tokens: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Calculate SHAP values for each token using perturbation method.
        
        This method removes each token and measures the impact on the score,
        which approximates SHAP values for text.
        """
        token_shap = []
        full_text_score = max(self.model.predict(text).values())
        
        for token in tokens:
            # Create text without this token
            # Use word boundaries to avoid partial matches
            import re
            pattern = r'\b' + re.escape(token) + r'\b'
            text_without_token = re.sub(pattern, '', text, count=1).strip()
            text_without_token = re.sub(r'\s+', ' ', text_without_token)  # Clean up extra spaces
            
            if not text_without_token:
                continue
            
            try:
                score_without = max(self.model.predict(text_without_token).values())
                token_impact = full_text_score - score_without
                
                # Normalize impact
                impact_magnitude = abs(token_impact)
                impact_level = (
                    "high" if impact_magnitude > 0.1
                    else "medium" if impact_magnitude > 0.05
                    else "low"
                )
                
                token_shap.append({
                    "token": token,
                    "shap_value": float(token_impact),
                    "impact": impact_level,
                    "contribution": "positive" if token_impact > 0 else "negative",
                })
            except Exception as e:
                # If token removal fails, skip or use small default
                token_shap.append({
                    "token": token,
                    "shap_value": 0.0,
                    "impact": "low",
                    "contribution": "neutral",
                })
        
        return token_shap
    
    def _get_category_explanations(self, text: str) -> Dict[str, Any]:
        """Get category-level SHAP explanations."""
        try:
            result = self.model.predict(text)
            
            category_explanations = {}
            for category, score in result.items():
                # Calculate contribution of this category to overall toxicity
                category_explanations[category] = {
                    "score": float(score),
                    "contribution": "high" if score > 0.7 else "medium" if score > 0.5 else "low",
                    "explanation": self._get_category_description(category, score),
                }
            
            return category_explanations
        except Exception:
            return {}
    
    def _get_category_description(self, category: str, score: float) -> str:
        """Get human-readable description for category."""
        descriptions = {
            "toxicity": "General toxic language detected",
            "severe_toxicity": "Severely toxic content requiring immediate attention",
            "obscene": "Obscene or profane language",
            "threat": "Threatening or violent language",
            "insult": "Insulting or derogatory language",
            "identity_attack": "Identity-based hate or attack",
        }
        
        base_desc = descriptions.get(category, f"{category} detected")
        if score > 0.7:
            return f"{base_desc} (high confidence)"
        elif score > 0.5:
            return f"{base_desc} (medium confidence)"
        else:
            return f"{base_desc} (low confidence)"
    
    def _generate_summary(
        self,
        feature_importance: List[Dict[str, Any]],
        category_explanations: Dict[str, Any],
    ) -> str:
        """Generate human-readable explanation summary."""
        top_tokens = [f for f in feature_importance[:5] if f["impact"] in ["high", "medium"]]
        
        if top_tokens:
            token_list = ", ".join([t["token"] for t in top_tokens])
            summary = f"Key contributors to toxicity: {token_list}. "
        else:
            summary = ""
        
        # Add category information
        high_impact_categories = [
            cat
            for cat, info in category_explanations.items()
            if info["contribution"] == "high"
        ]
        
        if high_impact_categories:
            summary += f"Primary categories: {', '.join(high_impact_categories)}."
        
        return summary.strip() or "Toxicity detected but no specific contributors identified."
    
    def _fallback_explanation(self, text: str) -> Dict[str, Any]:
        """Fallback explanation when SHAP fails."""
        return {
            "base_value": 0.0,
            "tokens": [],
            "feature_importance": [],
            "category_explanations": {},
            "total_shap_value": 0.0,
            "explanation_summary": "SHAP explanation unavailable. Using basic explanation.",
            "error": "SHAP explainer not initialized",
        }


# Global explainer instance
_toxicity_shap_explainer: Optional[ToxicitySHAPExplainer] = None


def get_toxicity_shap_explainer(
    model: Optional[Union[Detoxify, "DetoxifyToxicityDetector"]] = None,
) -> Optional[ToxicitySHAPExplainer]:
    """Get or create global SHAP explainer instance."""
    global _toxicity_shap_explainer
    
    if model and _toxicity_shap_explainer is None:
        _toxicity_shap_explainer = ToxicitySHAPExplainer(model)
    
    return _toxicity_shap_explainer

