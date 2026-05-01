"""
Remediation service for unsafe content.
"""

import re
from typing import Dict, Any, List

from openai import OpenAI

from ..core.config import get_settings
from .detoxify_toxicity import get_detoxify_detector
from .enhanced_bias import get_bias_detector

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
        if issue == "bias":
            return await self._remediate_bias(text)
        return {
            "remediated_text": text,
            "original_score": 0.0,
            "new_score": 0.0,
            "changes_made": [],
        }

    def _diff_changes(self, original: str, remediated: str, kind: str) -> List[str]:
        changes: List[str] = []
        if remediated.strip() == original.strip():
            changes.append("no_text_change")
            return changes
        if kind == "toxicity":
            changes.append("removed_toxic_language")
        else:
            changes.append("removed_bias")
        changes.append("content_rewrite")
        return changes

    async def _remediate_toxicity(self, text: str) -> Dict[str, Any]:
        """Remediate toxic content."""
        detector = get_detoxify_detector()
        orig = await detector.analyze(text)
        original_score = float(orig.get("toxicity_score", 0.0))

        if self.client:
            remediated = await self._llm_rephrase(
                text,
                "Rewrite this text to remove any toxic, offensive, or harmful language while preserving the core message. Be polite and professional.",
            )
        else:
            remediated = self._simple_detox(text)

        new_res = await detector.analyze(remediated)
        new_score = float(new_res.get("toxicity_score", 0.0))

        return {
            "remediated_text": remediated,
            "original_score": original_score,
            "new_score": new_score,
            "changes_made": self._diff_changes(text, remediated, "toxicity"),
        }

    async def _remediate_bias(self, text: str) -> Dict[str, Any]:
        """Remediate biased content."""
        detector = get_bias_detector()
        orig = await detector.analyze_comprehensive(
            prompt=text,
            response=text,
            demographic_variants=None,
        )
        original_score = float(orig.get("bias_score", 0.0))

        if self.client:
            remediated = await self._llm_rephrase(
                text,
                "Rewrite this text to remove any demographic bias, stereotypes, or assumptions. Use neutral, inclusive language.",
            )
        else:
            remediated = self._remove_gendered_qualifiers(text)

        new_res = await detector.analyze_comprehensive(
            prompt=remediated,
            response=remediated,
            demographic_variants=None,
        )
        new_score = float(new_res.get("bias_score", 0.0))

        return {
            "remediated_text": remediated,
            "original_score": original_score,
            "new_score": new_score,
            "changes_made": self._diff_changes(text, remediated, "bias"),
        }

    async def _llm_rephrase(self, text: str, instruction: str) -> str:
        """Use LLM to rephrase text."""
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": instruction},
                    {"role": "user", "content": text},
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
            r"\bstupid\b": "unwise",
            r"\bidiot\b": "person",
            r"\bdumb\b": "incorrect",
            r"\bhate\b": "dislike",
            r"\bfuck\b": "[removed]",
            r"\bshit\b": "[removed]",
            r"\bdamn\b": "[removed]",
        }

        result = text
        for pattern, replacement in replacements.items():
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

        return result

    def _remove_gendered_qualifiers(self, text: str) -> str:
        """Remove unnecessary gendered qualifiers."""
        return re.sub(
            r"\b(female|male|woman|man) (doctor|engineer|CEO|programmer|nurse)\b",
            r"\2",
            text,
            flags=re.IGNORECASE,
        )
