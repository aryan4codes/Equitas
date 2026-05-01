"""
LIME explainer for hallucination detection.
Provides sentence-level and claim-level explanations for hallucinations.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
from typing import Any, Coroutine, Dict, List, Optional, TypeVar

from lime.lime_text import LimeTextExplainer
import numpy as np

from ..core.config import get_settings

settings = get_settings()

T = TypeVar("T")


def _run_coro_sync(coro: Coroutine[Any, Any, T]) -> T:
    """Run an async coroutine from sync code (safe when a loop is already running)."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    def _in_thread() -> T:
        new_loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(new_loop)
            return new_loop.run_until_complete(coro)
        finally:
            try:
                new_loop.run_until_complete(new_loop.shutdown_asyncgens())
            except Exception:
                pass
            new_loop.close()
            asyncio.set_event_loop(None)

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(_in_thread).result()


class HallucinationLIMEExplainer:
    """
    LIME explainer for hallucination detection.
    
    Provides explanations for:
    - Which sentences contribute to hallucination score
    - Which claims are unsupported or contradicted
    - Context relevance analysis
    """
    
    def __init__(self, hallucination_detector):
        """
        Initialize LIME explainer for hallucination detection.
        
        Args:
            hallucination_detector: HallucinationDetector instance
        """
        self.detector = hallucination_detector
        self.explainer = LimeTextExplainer(class_names=['factual', 'hallucinated'])
        self._embedder: Optional[Any] = None
        try:
            from sentence_transformers import SentenceTransformer

            self._embedder = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception as e:
            print(f"LIME: SentenceTransformer cache init failed: {e}")
            self._embedder = None
    
    def explain(
        self,
        prompt: str,
        response: str,
        context: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Generate LIME explanation for hallucination detection.
        
        Args:
            prompt: Original prompt
            response: LLM response to explain
            context: Optional context/knowledge base
        
        Returns:
            Dict with LIME explanations for sentences and claims
        """
        try:
            # Split response into sentences
            sentences = self._split_into_sentences(response)
            
            # Get sentence-level explanations
            sentence_explanations = self._explain_sentences(
                prompt, sentences, context
            )
            
            # Get claim-level explanations
            claim_explanations = self._explain_claims(
                prompt, response, context
            )
            
            # Generate overall explanation
            overall_explanation = self._generate_overall_explanation(
                sentence_explanations, claim_explanations
            )
            
            return {
                "sentences": sentence_explanations,
                "claims": claim_explanations,
                "overall_explanation": overall_explanation,
                "summary": self._generate_summary(sentence_explanations),
            }
        except Exception as e:
            print(f"LIME explanation failed: {e}")
            return self._fallback_explanation(response)
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        import re
        # Simple sentence splitting
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]

    def _detect_sync(
        self,
        prompt: str,
        response: str,
        context: Optional[List[str]],
    ) -> Dict[str, Any]:
        """Call async HallucinationDetector.detect from synchronous LIME code paths."""
        return _run_coro_sync(
            self.detector.detect(prompt=prompt, response=response, context=context)
        )
    
    def _explain_sentences(
        self,
        prompt: str,
        sentences: List[str],
        context: Optional[List[str]],
    ) -> List[Dict[str, Any]]:
        """Generate LIME explanations for each sentence."""
        sentence_explanations = []
        
        for sentence in sentences:
            try:
                # Create full text with and without this sentence
                full_text = " ".join(sentences)
                
                # Get score with sentence
                result_with = self._detect_sync(
                    prompt=prompt,
                    response=full_text,
                    context=context,
                )
                score_with = result_with.get("hallucination_score", 0.0)
                
                # Get score without sentence
                sentences_without = [s for s in sentences if s != sentence]
                text_without = " ".join(sentences_without)
                
                if text_without:
                    result_without = self._detect_sync(
                        prompt=prompt,
                        response=text_without,
                        context=context,
                    )
                    score_without = result_without.get("hallucination_score", 0.0)
                else:
                    score_without = 0.0
                
                # Calculate sentence impact
                impact = score_with - score_without
                
                # Use LIME to explain sentence
                lime_explanation = self.explainer.explain_instance(
                    sentence,
                    self._predict_sentence,
                    num_features=5,
                    top_labels=1,
                )
                
                # Extract features
                features = lime_explanation.as_list()
                
                sentence_explanations.append({
                    "sentence": sentence,
                    "hallucination_score": float(score_with),
                    "impact": float(impact),
                    "impact_level": (
                        "high" if abs(impact) > 0.2
                        else "medium" if abs(impact) > 0.1
                        else "low"
                    ),
                    "features": [
                        {
                            "feature": feat[0],
                            "weight": float(feat[1]),
                            "contribution": "positive" if feat[1] > 0 else "negative",
                        }
                        for feat in features
                    ],
                    "explanation": self._explain_sentence_impact(
                        sentence, impact, features
                    ),
                })
            except Exception as e:
                print(f"Failed to explain sentence: {e}")
                sentence_explanations.append({
                    "sentence": sentence,
                    "hallucination_score": 0.0,
                    "impact": 0.0,
                    "impact_level": "unknown",
                    "features": [],
                    "explanation": "Unable to generate explanation.",
                })
        
        return sentence_explanations
    
    def _predict_sentence(self, sentences: List[str]) -> np.ndarray:
        """Predict function for LIME."""
        scores = []
        for sentence in sentences:
            try:
                # Simplified prediction for LIME
                # This should use a faster proxy model
                result = self._detect_sync(
                    prompt="",
                    response=sentence,
                    context=None,
                )
                score = float(result.get("hallucination_score", 0.0))
                scores.append([1.0 - score, score])  # [factual, hallucinated]
            except Exception:
                scores.append([0.5, 0.5])
        
        return np.array(scores)
    
    def _explain_claims(
        self,
        prompt: str,
        response: str,
        context: Optional[List[str]],
    ) -> List[Dict[str, Any]]:
        """Explain specific claims in the response."""
        # Extract claims (simplified - can be enhanced with NER)
        claims = self._extract_claims(response)
        
        claim_explanations = []
        for claim in claims:
            try:
                # Check if claim is supported by context
                support_score = self._check_claim_support(claim, context)
                
                # Check if claim contradicts context
                contradiction_score = self._check_contradiction(claim, context)
                
                claim_explanations.append({
                    "claim": claim,
                    "support_score": float(support_score),
                    "contradiction_score": float(contradiction_score),
                    "status": (
                        "unsupported" if support_score < 0.3
                        else "contradicted" if contradiction_score > 0.5
                        else "supported"
                    ),
                    "explanation": self._explain_claim_status(
                        claim, support_score, contradiction_score
                    ),
                })
            except Exception:
                continue
        
        return claim_explanations
    
    def _extract_claims(self, text: str) -> List[str]:
        """Extract factual claims from text (simplified)."""
        # Simple claim extraction - can be enhanced
        import re
        # Look for statements with dates, numbers, or specific facts
        claims = []
        sentences = self._split_into_sentences(text)
        
        for sentence in sentences:
            # Check if sentence contains factual indicators
            if re.search(r'\d{4}|\d+%|million|billion|founded|established', sentence):
                claims.append(sentence)
        
        return claims[:5]  # Limit to top 5 claims
    
    def _check_claim_support(
        self, claim: str, context: Optional[List[str]]
    ) -> float:
        """Check if claim is supported by context."""
        if not context:
            return 0.0  # No context to verify
        
        if not self._embedder:
            return 0.0

        try:
            claim_embedding = self._embedder.encode(claim, convert_to_numpy=True)
            
            max_similarity = 0.0
            for ctx_text in context:
                ctx_embedding = self._embedder.encode(ctx_text, convert_to_numpy=True)
                similarity = np.dot(claim_embedding, ctx_embedding) / (
                    np.linalg.norm(claim_embedding) * np.linalg.norm(ctx_embedding)
                )
                max_similarity = max(max_similarity, similarity)
            
            return float(max_similarity)
        except Exception:
            return 0.0
    
    def _check_contradiction(
        self, claim: str, context: Optional[List[str]]
    ) -> float:
        """Check if claim contradicts context."""
        # Simplified contradiction detection
        # In production, use NLI models
        return 0.0  # Placeholder
    
    def _explain_sentence_impact(
        self, sentence: str, impact: float, features: List[tuple]
    ) -> str:
        """Generate explanation for sentence impact."""
        if abs(impact) < 0.05:
            return "This sentence has minimal impact on hallucination score."
        
        top_features = sorted(features, key=lambda x: abs(x[1]), reverse=True)[:3]
        feature_names = [f[0] for f in top_features]
        
        if impact > 0:
            return (
                f"This sentence increases hallucination score by {impact:.2f}. "
                f"Key features: {', '.join(feature_names)}."
            )
        else:
            return (
                f"This sentence decreases hallucination score by {abs(impact):.2f}. "
                f"Key features: {', '.join(feature_names)}."
            )
    
    def _explain_claim_status(
        self, claim: str, support_score: float, contradiction_score: float
    ) -> str:
        """Explain claim status."""
        if contradiction_score > 0.5:
            return f"Claim contradicts provided context (contradiction score: {contradiction_score:.2f})."
        elif support_score < 0.3:
            return f"Claim not supported by context (support score: {support_score:.2f})."
        else:
            return f"Claim supported by context (support score: {support_score:.2f})."
    
    def _generate_overall_explanation(
        self,
        sentence_explanations: List[Dict[str, Any]],
        claim_explanations: List[Dict[str, Any]],
    ) -> str:
        """Generate overall explanation."""
        high_impact_sentences = [
            s for s in sentence_explanations if s["impact_level"] == "high"
        ]
        
        unsupported_claims = [
            c for c in claim_explanations if c["status"] == "unsupported"
        ]
        
        parts = []
        if high_impact_sentences:
            parts.append(
                f"{len(high_impact_sentences)} sentence(s) significantly contribute to hallucination."
            )
        if unsupported_claims:
            parts.append(
                f"{len(unsupported_claims)} claim(s) are unsupported by context."
            )
        
        if not parts:
            return "No significant hallucinations detected."
        
        return " ".join(parts)
    
    def _generate_summary(
        self, sentence_explanations: List[Dict[str, Any]]
    ) -> str:
        """Generate concise summary."""
        top_sentences = sorted(
            sentence_explanations,
            key=lambda x: abs(x["impact"]),
            reverse=True
        )[:3]
        
        if top_sentences:
            sentence_texts = [s["sentence"][:50] + "..." for s in top_sentences]
            return f"Top contributors: {'; '.join(sentence_texts)}"
        
        return "No significant contributors identified."
    
    def _fallback_explanation(self, response: str) -> Dict[str, Any]:
        """Fallback explanation when LIME fails."""
        return {
            "sentences": [],
            "claims": [],
            "overall_explanation": "LIME explanation unavailable.",
            "summary": "Unable to generate detailed explanation.",
            "error": "LIME explainer failed",
        }


# Global explainer instance
_hallucination_lime_explainer: Optional[HallucinationLIMEExplainer] = None


def get_hallucination_lime_explainer(hallucination_detector) -> HallucinationLIMEExplainer:
    """Get or create global LIME explainer instance."""
    global _hallucination_lime_explainer
    if _hallucination_lime_explainer is None:
        _hallucination_lime_explainer = HallucinationLIMEExplainer(hallucination_detector)
    return _hallucination_lime_explainer

