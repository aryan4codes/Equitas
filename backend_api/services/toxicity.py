"""
Toxicity detection service using OpenAI Moderation API.
"""

import re
from typing import Dict, Any, List
from openai import OpenAI

from ..core.config import get_settings

settings = get_settings()


class ToxicityDetector:
    """Detects toxic content using OpenAI's Moderation API."""
    
    def __init__(self):
        if settings.openai_api_key:
            self.client = OpenAI(api_key=settings.openai_api_key)
        else:
            self.client = None
        
        # Fallback: Simple pattern-based detection
        self.toxic_patterns = [
            r'\b(hate|stupid|idiot|dumb|kill|die)\b',
            r'\b(fuck|shit|damn|bitch|asshole)\b',
        ]
    
    async def analyze(self, text: str) -> Dict[str, Any]:
        """
        Analyze text for toxicity.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dict with toxicity_score, flagged, and categories
        """
        if self.client:
            return await self._analyze_with_openai(text)
        else:
            return await self._analyze_with_patterns(text)
    
    async def _analyze_with_openai(self, text: str) -> Dict[str, Any]:
        """Analyze using OpenAI Moderation API."""
        try:
            response = self.client.moderations.create(input=text)
            result = response.results[0]
            
            # Extract categories that are flagged
            flagged_categories = [
                category
                for category, flagged in result.categories.model_dump().items()
                if flagged
            ]
            
            # Compute overall toxicity score (max of category scores)
            category_scores = result.category_scores.model_dump()
            toxicity_score = max(category_scores.values()) if category_scores else 0.0
            
            return {
                "toxicity_score": toxicity_score,
                "flagged": result.flagged,
                "categories": flagged_categories,
            }
        except Exception as e:
            print(f"OpenAI moderation failed: {e}")
            return await self._analyze_with_patterns(text)
    
    async def _analyze_with_patterns(self, text: str) -> Dict[str, Any]:
        """Fallback pattern-based detection."""
        text_lower = text.lower()
        flagged = False
        categories = []
        
        for pattern in self.toxic_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                flagged = True
                categories.append("inappropriate-language")
                break
        
        toxicity_score = 0.8 if flagged else 0.0
        
        return {
            "toxicity_score": toxicity_score,
            "flagged": flagged,
            "categories": categories,
        }
