"""
Hallucination detection service using multiple techniques:
1. Semantic consistency checks
2. Contradiction detection
3. Factuality checking
4. Pattern-based detection
5. Confidence calibration
"""

from typing import Dict, Any, List, Optional
import numpy as np
from sentence_transformers import SentenceTransformer

try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

from ..core.config import get_settings

settings = get_settings()


class HallucinationDetector:
    """
    Detects hallucinations using multi-component ensemble approach.
    
    Components:
    - Semantic consistency (prompt vs response)
    - Contradiction detection (internal consistency)
    - Factuality check (against knowledge base)
    - Pattern-based detection
    - Confidence calibration
    """
    
    def __init__(self):
        """Initialize hallucination detector."""
        try:
            # For semantic similarity
            self.similarity_model = SentenceTransformer('all-MiniLM-L6-v2')
            
            # For contradiction detection
            if TRANSFORMERS_AVAILABLE:
                try:
                    self.contradiction_pipeline = pipeline(
                        "text-classification",
                        model="cross-encoder/nli-deberta-v3-base",
                        device=-1  # CPU
                    )
                    self.contradiction_available = True
                except Exception as e:
                    print(f"Contradiction model not available: {e}")
                    self.contradiction_available = False
            else:
                self.contradiction_available = False
            
            self.models_loaded = True
        except Exception as e:
            print(f"Failed to load hallucination models: {e}")
            self.models_loaded = False
        
        # Hallucination indicators
        self.hallucination_patterns = [
            r'\b(studies show|research proves|experts agree)\b',
            r'\b(it is a fact that|scientifically proven)\b',
            r'\b(no one knows|mystery|secret)\b',
            r'\b(definitely|absolutely|100%|guaranteed)\b',
        ]
    
    async def detect(
        self,
        prompt: str,
        response: str,
        context: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Detect hallucinations in response.
        
        Args:
            prompt: Original prompt
            response: LLM response
            context: Optional context/knowledge base for fact-checking
            
        Returns:
            Hallucination analysis with confidence scores
        """
        if not self.models_loaded:
            return {
                "hallucination_score": 0.0,
                "flagged": False,
                "confidence": 1.0,
                "components": {},
                "recommendation": "safe",
                "error": "Models not loaded"
            }
        
        results = {}
        
        # 1. Semantic consistency check
        consistency_score = await self._check_consistency(prompt, response)
        results["consistency_score"] = consistency_score
        
        # 2. Contradiction detection
        contradiction_score = await self._check_contradictions(response)
        results["contradiction_score"] = contradiction_score
        
        # 3. Factuality check (if context provided)
        if context:
            factuality_score = await self._check_factuality(response, context)
            results["factuality_score"] = factuality_score
        else:
            factuality_score = None
        
        # 4. Pattern-based detection
        pattern_score = await self._check_patterns(response)
        results["pattern_score"] = pattern_score
        
        # 5. Confidence calibration
        confidence_score = await self._calibrate_confidence(response)
        results["confidence_score"] = confidence_score
        
        # Compute overall hallucination score
        scores = [
            consistency_score,
            contradiction_score,
            pattern_score,
            confidence_score
        ]
        if factuality_score is not None:
            scores.append(factuality_score)
        
        overall_score = np.mean(scores)
        flagged = overall_score > 0.6
        
        return {
            "hallucination_score": float(overall_score),
            "flagged": flagged,
            "confidence": float(1.0 - overall_score),  # Inverse: lower hallucination = higher confidence
            "components": results,
            "recommendation": self._get_recommendation(overall_score)
        }
    
    async def _check_consistency(self, prompt: str, response: str) -> float:
        """Check semantic consistency between prompt and response."""
        try:
            # Encode prompt and response
            prompt_embedding = self.similarity_model.encode(prompt)
            response_embedding = self.similarity_model.encode(response)
            
            # Calculate cosine similarity
            similarity = np.dot(prompt_embedding, response_embedding) / (
                np.linalg.norm(prompt_embedding) * np.linalg.norm(response_embedding)
            )
            
            # Low similarity = potential hallucination
            # Clamp to [0, 1]
            return float(max(0.0, min(1.0, 1.0 - similarity)))
        except Exception as e:
            print(f"Consistency check failed: {e}")
            return 0.5  # Neutral score on error
    
    async def _check_contradictions(self, text: str) -> float:
        """Check for internal contradictions."""
        if not self.contradiction_available:
            return 0.0
        
        try:
            sentences = [s.strip() for s in text.split('.') if len(s.strip()) > 10]
            if len(sentences) < 2:
                return 0.0
            
            contradictions = 0
            total_pairs = 0
            
            # Check pairs of sentences for contradictions
            for i in range(len(sentences) - 1):
                for j in range(i + 1, len(sentences)):
                    sent1 = sentences[i]
                    sent2 = sentences[j]
                    
                    if len(sent1) < 10 or len(sent2) < 10:
                        continue
                    
                    try:
                        # Use NLI model to detect contradiction
                        result = self.contradiction_pipeline(f"{sent1} [SEP] {sent2}")
                        if isinstance(result, list):
                            result = result[0]
                        
                        label = result.get('label', '').upper()
                        if 'CONTRADICTION' in label:
                            contradictions += 1
                        total_pairs += 1
                    except Exception:
                        continue
            
            if total_pairs == 0:
                return 0.0
            
            return float(contradictions / total_pairs)
        except Exception as e:
            print(f"Contradiction check failed: {e}")
            return 0.0
    
    async def _check_factuality(self, response: str, context: List[str]) -> float:
        """Check factuality against provided context."""
        try:
            response_embedding = self.similarity_model.encode(response)
            
            max_similarity = 0.0
            for ctx_text in context:
                ctx_embedding = self.similarity_model.encode(ctx_text)
                similarity = np.dot(response_embedding, ctx_embedding) / (
                    np.linalg.norm(response_embedding) * np.linalg.norm(ctx_embedding)
                )
                max_similarity = max(max_similarity, similarity)
            
            # Low similarity to context = potential hallucination
            return float(1.0 - max_similarity)
        except Exception as e:
            print(f"Factuality check failed: {e}")
            return 0.5  # Neutral score
    
    async def _check_patterns(self, text: str) -> float:
        """Check for hallucination-indicating patterns."""
        import re
        text_lower = text.lower()
        matches = sum(1 for pattern in self.hallucination_patterns 
                     if re.search(pattern, text_lower))
        
        return float(min(matches * 0.2, 1.0))
    
    async def _calibrate_confidence(self, text: str) -> float:
        """Estimate confidence based on linguistic markers."""
        import re
        
        # High confidence markers = potential hallucination
        high_confidence_markers = [
            r'\b(definitely|absolutely|certainly|undoubtedly)\b',
            r'\b(proven|fact|truth|reality)\b',
            r'\b(always|never|all|none)\b',
        ]
        
        low_confidence_markers = [
            r'\b(maybe|perhaps|possibly|might)\b',
            r'\b(according to|sources suggest|studies indicate)\b',
            r'\b(generally|often|typically|usually)\b',
        ]
        
        text_lower = text.lower()
        
        high_count = sum(1 for pattern in high_confidence_markers 
                        if re.search(pattern, text_lower))
        low_count = sum(1 for pattern in low_confidence_markers 
                       if re.search(pattern, text_lower))
        
        # More high-confidence markers = higher hallucination risk
        if high_count + low_count == 0:
            return 0.5  # Neutral
        
        return float(high_count / (high_count + low_count + 1))
    
    def _get_recommendation(self, score: float) -> str:
        """Get recommendation based on hallucination score."""
        if score > 0.8:
            return "high_risk"
        elif score > 0.6:
            return "medium_risk"
        elif score > 0.4:
            return "low_risk"
        else:
            return "safe"


# Global detector instance
_hallucination_detector: Optional[HallucinationDetector] = None


def get_hallucination_detector() -> HallucinationDetector:
    """Get or create global hallucination detector instance."""
    global _hallucination_detector
    if _hallucination_detector is None:
        _hallucination_detector = HallucinationDetector()
    return _hallucination_detector

