"""
Custom toxicity detection service using transformer models.
Replaces OpenAI Moderation API with open-source models.
"""

import torch
from typing import Dict, Any, List, Optional
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import numpy as np

from ..core.config import get_settings

settings = get_settings()


class CustomToxicityDetector:
    """
    Detects toxic content using open-source transformer models.
    
    Uses models like:
    - unitary/toxic-bert (RoBERTa-based)
    - facebook/roberta-hate-speech-dynabench
    """
    
    def __init__(self, model_name: str = "unitary/toxic-bert"):
        """
        Initialize toxicity detector.
        
        Args:
            model_name: HuggingFace model identifier
        """
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_name = model_name
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
            self.model.to(self.device)
            self.model.eval()
            self.model_loaded = True
        except Exception as e:
            print(f"Failed to load model {model_name}: {e}")
            self.model_loaded = False
        
        # Category mapping for toxic-bert
        self.category_map = {
            0: "toxic",
            1: "severe_toxic",
            2: "obscene",
            3: "threat",
            4: "insult",
            5: "identity_hate"
        }
        
        # Threshold for flagging
        self.threshold = 0.7
    
    async def analyze(self, text: str) -> Dict[str, Any]:
        """
        Analyze text for toxicity.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dict with toxicity_score, flagged, and categories
        """
        if not self.model_loaded:
            return await self._fallback_analysis(text)
        
        return await self._analyze_with_model(text)
    
    async def _analyze_with_model(self, text: str) -> Dict[str, Any]:
        """Analyze using transformer model."""
        try:
            # Tokenize input
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True
            )
            
            # Move to device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Inference
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                
                # Apply sigmoid for multi-label classification
                probs = torch.sigmoid(logits).cpu().numpy()[0]
            
            # Extract categories that are flagged
            categories = []
            category_scores = {}
            max_score = 0.0
            
            for idx, category_name in self.category_map.items():
                if idx < len(probs):
                    score = float(probs[idx])
                    category_scores[category_name] = score
                    if score > 0.5:  # Category threshold
                        categories.append(category_name)
                    max_score = max(max_score, score)
            
            # Overall toxicity score is the maximum category score
            flagged = max_score > self.threshold
            
            return {
                "toxicity_score": max_score,
                "flagged": flagged,
                "categories": categories,
                "category_scores": category_scores,
            }
        except Exception as e:
            print(f"Model inference failed: {e}")
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
        }
    
    def update_threshold(self, threshold: float):
        """Update toxicity threshold."""
        if 0.0 <= threshold <= 1.0:
            self.threshold = threshold
        else:
            raise ValueError("Threshold must be between 0 and 1")


# Global detector instance
_toxicity_detector: Optional[CustomToxicityDetector] = None


def get_toxicity_detector(model_name: str = "unitary/toxic-bert") -> CustomToxicityDetector:
    """Get or create global toxicity detector instance."""
    global _toxicity_detector
    if _toxicity_detector is None:
        _toxicity_detector = CustomToxicityDetector(model_name)
    return _toxicity_detector

