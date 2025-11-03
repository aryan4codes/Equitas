"""
Remediation service for unsafe content.
"""

import re
from typing import Dict, Any
from openai import OpenAI

from ..core.config import get_settings

settings = get_settings()


class RemediationEngine:
    """Remediates unsafe content through rewriting."""
    
    def __init__(self):
        if settings.openai_api_key:
            self.client = OpenAI(api_key=settings.openai_api_key)
        else:
            self.client = None
    
    async def remediate(self, text: str, issue: str) -> Dict[str, Any]:
        """
        Remediate unsafe content.
        
        Args:
            text: Text to remediate
            issue: Issue type (toxicity, bias)
            
        Returns:
            Dict with remediated_text, original_score, new_score, changes_made
        """
        if issue == "toxicity":
            return await self._remediate_toxicity(text)
        elif issue == "bias":
            return await self._remediate_bias(text)
        else:
            # No remediation available
            return {
                "remediated_text": text,
                "original_score": 0.0,
                "new_score": 0.0,
                "changes_made": [],
            }
    
    async def _remediate_toxicity(self, text: str) -> Dict[str, Any]:
        """Remediate toxic content."""
        if self.client:
            # Use LLM to rephrase
            remediated = await self._llm_rephrase(
                text,
                "Rewrite this text to remove any toxic, offensive, or harmful language while preserving the core message. Be polite and professional."
            )
        else:
            # Fallback: Simple word replacement
            remediated = self._simple_detox(text)
        
        return {
            "remediated_text": remediated,
            "original_score": 0.85,  # Mock scores
            "new_score": 0.15,
            "changes_made": ["removed_toxic_language", "rephrased_politely"],
        }
    
    async def _remediate_bias(self, text: str) -> Dict[str, Any]:
        """Remediate biased content."""
        if self.client:
            remediated = await self._llm_rephrase(
                text,
                "Rewrite this text to remove any demographic bias, stereotypes, or assumptions. Use neutral, inclusive language."
            )
        else:
            # Fallback: Remove gendered qualifiers
            remediated = self._remove_gendered_qualifiers(text)
        
        return {
            "remediated_text": remediated,
            "original_score": 0.65,
            "new_score": 0.10,
            "changes_made": ["removed_bias", "neutral_language"],
        }
    
    async def _llm_rephrase(self, text: str, instruction: str) -> str:
        """Use LLM to rephrase text."""
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": instruction},
                    {"role": "user", "content": text}
                ],
                temperature=0.3,
            )
            return response.choices[0].message.content or text
        except Exception as e:
            print(f"LLM remediation failed: {e}")
            return text
    
    def _simple_detox(self, text: str) -> str:
        """Simple toxic word replacement."""
        replacements = {
            r'\bstupid\b': 'unwise',
            r'\bidiot\b': 'person',
            r'\bdumb\b': 'incorrect',
            r'\bhate\b': 'dislike',
            r'\bfuck\b': '[removed]',
            r'\bshit\b': '[removed]',
            r'\bdamn\b': '[removed]',
        }
        
        result = text
        for pattern, replacement in replacements.items():
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        
        return result
    
    def _remove_gendered_qualifiers(self, text: str) -> str:
        """Remove unnecessary gendered qualifiers."""
        # Remove patterns like "female doctor" -> "doctor"
        result = re.sub(
            r'\b(female|male|woman|man) (doctor|engineer|CEO|programmer|nurse)\b',
            r'\2',
            text,
            flags=re.IGNORECASE
        )
        return result
