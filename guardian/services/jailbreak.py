"""
Jailbreak and prompt injection detection service.
"""

import re
from typing import Dict, Any, List


class JailbreakDetector:
    """Detects jailbreak attempts and prompt injections."""
    
    def __init__(self):
        # Known jailbreak patterns
        self.jailbreak_patterns = [
            r'ignore (previous|all previous|the above|all) (instructions|commands|prompts)',
            r'disregard (previous|all previous|the above)',
            r'forget (everything|all|previous)',
            r'new instructions:',
            r'system prompt:',
            r'you are now',
            r'pretend (you are|to be)',
            r'roleplay as',
            r'act as (if )?you',
            r'do anything now',
            r'DAN mode',
            r'jailbreak',
            r'sudo ',
            r'</system>',
            r'<\|im_end\|>',
            r'\[INST\]',
        ]
        
        # Patterns that might indicate code injection
        self.injection_patterns = [
            r'<script>',
            r'javascript:',
            r'eval\(',
            r'exec\(',
            r'__import__',
            r'subprocess',
        ]
    
    async def detect(self, text: str) -> Dict[str, Any]:
        """
        Detect jailbreak attempts.
        
        Args:
            text: Text to analyze (prompt or response)
            
        Returns:
            Dict with jailbreak_flag, confidence, and patterns_detected
        """
        text_lower = text.lower()
        detected_patterns = []
        
        # Check jailbreak patterns
        for pattern in self.jailbreak_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                detected_patterns.append(f"jailbreak: {pattern}")
        
        # Check injection patterns
        for pattern in self.injection_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                detected_patterns.append(f"injection: {pattern}")
        
        jailbreak_flag = len(detected_patterns) > 0
        confidence = min(len(detected_patterns) * 0.3, 1.0)
        
        return {
            "jailbreak_flag": jailbreak_flag,
            "confidence": confidence,
            "patterns_detected": detected_patterns,
        }
