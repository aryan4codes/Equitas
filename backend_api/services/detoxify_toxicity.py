"""
Toxicity detection using Detoxify library.
Simpler and more maintainable than custom transformer implementation.
"""

from typing import Dict, Any, Optional
from detoxify import Detoxify

from ..core.config import get_settings

settings = get_settings()


class DetoxifyToxicityDetector:
    """
    Detects toxic content using Detoxify library.
    
    Detoxify provides pre-trained models:
    - 'original': Original model trained on Jigsaw dataset
    - 'unbiased': Debiased model
    - 'multilingual': Multilingual toxicity detection
    
    Categories detected:
    - toxicity
    - severe_toxicity
    - obscene
    - threat
    - insult
    - identity_attack
    """
    
    def __init__(self, model_name: str = "original"):
        """
        Initialize Detoxify toxicity detector.
        
        Args:
            model_name: One of 'original', 'unbiased', 'multilingual'
        """
        self.model_name = model_name
        self.model: Optional[Detoxify] = None
        self.model_loaded = False
        
        # Threshold for flagging
        self.threshold = 0.7
        
        try:
            self.model = Detoxify(model_name)
            self.model_loaded = True
        except Exception as e:
            print(f"Failed to load Detoxify model {model_name}: {e}")
            self.model_loaded = False

    def predict(self, text: str) -> Dict[str, float]:
        """
        Synchronous Detoxify forward pass for SHAP/token perturbation code paths.
        Returns category -> score (empty dict if model unavailable).
        """
        if not self.model_loaded or not self.model:
            return {}
        try:
            raw = self.model.predict(text)
            return {k: float(v) for k, v in raw.items()}
        except Exception as e:
            print(f"Detoxify predict failed: {e}")
            return {}
    
    async def analyze(self, text: str) -> Dict[str, Any]:
        """
        Analyze text for toxicity using Detoxify.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dict with toxicity_score, flagged, categories, and category_scores
        """
        if not self.model_loaded or not self.model:
            return await self._fallback_analysis(text)
        
        try:
            # Detoxify returns a dictionary with scores for each category
            results = self.model.predict(text)
            
            # Extract categories that are flagged
            categories = []
            category_scores = {}
            max_score = 0.0
            
            for category, score in results.items():
                category_scores[category] = float(score)
                if score > 0.5:  # Category threshold
                    categories.append(category)
                max_score = max(max_score, score)
            
            # Overall toxicity score is the maximum category score
            flagged = max_score > self.threshold
            
            return {
                "toxicity_score": float(max_score),
                "flagged": flagged,
                "categories": categories,
                "category_scores": category_scores,
                "model": self.model_name,
            }
        except Exception as e:
            print(f"Detoxify inference failed: {e}")
            return await self._fallback_analysis(text)
    
    async def _fallback_analysis(self, text: str) -> Dict[str, Any]:
        """Fallback pattern-based detection."""
        import re
        
        # Simple pattern-based fallback
        toxic_patterns = [
            r'\b(hate|stupid|idiot|dumb|kill|die)\b',
            r'\b(fuck|shit|damn|bitch|asshole)\b',
        ]
        
        text_lower = text.lower()
        flagged = False
        categories = []
        
        for pattern in toxic_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                flagged = True
                categories.append("inappropriate-language")
                break
        
        toxicity_score = 0.8 if flagged else 0.0
        
        return {
            "toxicity_score": toxicity_score,
            "flagged": flagged,
            "categories": categories,
            "category_scores": {"inappropriate-language": toxicity_score},
            "model": "fallback",
        }
    
    def update_threshold(self, threshold: float):
        """Update toxicity threshold."""
        if 0.0 <= threshold <= 1.0:
            self.threshold = threshold
        else:
            raise ValueError("Threshold must be between 0 and 1")


# Global detector instance
_detoxify_detector: Optional[DetoxifyToxicityDetector] = None


def get_detoxify_detector(model_name: str = "original") -> DetoxifyToxicityDetector:
    """Get or create global Detoxify detector instance."""
    global _detoxify_detector
    if _detoxify_detector is None:
        _detoxify_detector = DetoxifyToxicityDetector(model_name)
    return _detoxify_detector

