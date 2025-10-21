"""
Explainability service for safety violations.
"""

import re
from typing import Dict, Any, List


class ExplainabilityEngine:
    """Generates explanations for flagged content."""
    
    async def explain(self, text: str, issues: List[str]) -> Dict[str, Any]:
        """
        Generate explanation for flagged content.
        
        Args:
            text: The flagged text
            issues: List of issues (e.g., ["toxicity", "bias"])
            
        Returns:
            Dict with explanation and highlighted_spans
        """
        explanations = []
        highlighted_spans = []
        
        for issue in issues:
            if issue == "toxicity":
                toxicity_explanation = self._explain_toxicity(text)
                explanations.append(toxicity_explanation["explanation"])
                highlighted_spans.extend(toxicity_explanation.get("spans", []))
            
            elif issue == "bias":
                bias_explanation = self._explain_bias(text)
                explanations.append(bias_explanation["explanation"])
                highlighted_spans.extend(bias_explanation.get("spans", []))
            
            elif issue == "jailbreak":
                jailbreak_explanation = self._explain_jailbreak(text)
                explanations.append(jailbreak_explanation["explanation"])
                highlighted_spans.extend(jailbreak_explanation.get("spans", []))
        
        full_explanation = " ".join(explanations)
        
        return {
            "explanation": full_explanation,
            "highlighted_spans": highlighted_spans,
        }
    
    def _explain_toxicity(self, text: str) -> Dict[str, Any]:
        """Explain toxicity issues."""
        # Find toxic words/phrases
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
    
    def _explain_bias(self, text: str) -> Dict[str, Any]:
        """Explain bias issues."""
        # Detect biased phrases
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
