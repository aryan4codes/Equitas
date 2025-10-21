"""
Custom classifier system - Pluggable safety detectors.

This allows equitas to go beyond OpenAI Moderation API with custom,
domain-specific safety classifiers.
"""

import re
from typing import Dict, Any, List, Optional, Protocol
from abc import ABC, abstractmethod


class SafetyClassifier(Protocol):
    """Protocol for custom safety classifiers."""
    
    async def classify(self, text: str) -> Dict[str, Any]:
        """
        Classify text for safety issues.
        
        Returns:
            Dict with 'score' (0-1), 'flagged' (bool), and 'details' (dict)
        """
        ...


class BaseClassifier(ABC):
    """Base class for safety classifiers."""
    
    def __init__(self, name: str, threshold: float = 0.7):
        self.name = name
        self.threshold = threshold
    
    @abstractmethod
    async def classify(self, text: str) -> Dict[str, Any]:
        """Classify text."""
        pass


class PIIDetector(BaseClassifier):
    """Detects Personally Identifiable Information (PII)."""
    
    def __init__(self, threshold: float = 0.8):
        super().__init__("pii_detector", threshold)
        
        # PII patterns
        self.patterns = {
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "phone": r'\b(\+\d{1,2}\s?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b',
            "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
            "credit_card": r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
            "ip_address": r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
        }
    
    async def classify(self, text: str) -> Dict[str, Any]:
        """Detect PII in text."""
        found_pii = {}
        total_matches = 0
        
        for pii_type, pattern in self.patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                found_pii[pii_type] = len(matches)
                total_matches += len(matches)
        
        score = min(total_matches * 0.3, 1.0)
        flagged = score >= self.threshold
        
        return {
            "score": score,
            "flagged": flagged,
            "details": {
                "pii_types": found_pii,
                "total_occurrences": total_matches,
            },
            "category": "pii",
        }


class MisinformationDetector(BaseClassifier):
    """Detects potential misinformation patterns."""
    
    def __init__(self, threshold: float = 0.6):
        super().__init__("misinfo_detector", threshold)
        
        # Misinformation indicators
        self.indicators = [
            r'\b(definitely|absolutely|100%|guaranteed) (true|false|proven)\b',
            r'\b(scientists|doctors|experts) (don\'t want you to know|are hiding)\b',
            r'\b(miracle cure|secret|they don\'t tell you)\b',
            r'\b(fake news|mainstream media lies)\b',
            r'\ball (liberals|conservatives|democrats|republicans) (always|never)\b',
        ]
    
    async def classify(self, text: str) -> Dict[str, Any]:
        """Detect misinformation patterns."""
        text_lower = text.lower()
        matches = []
        
        for pattern in self.indicators:
            if re.search(pattern, text_lower, re.IGNORECASE):
                matches.append(pattern)
        
        score = min(len(matches) * 0.25, 1.0)
        flagged = score >= self.threshold
        
        return {
            "score": score,
            "flagged": flagged,
            "details": {
                "indicator_count": len(matches),
                "patterns": matches[:3],  # Top 3
            },
            "category": "misinformation",
        }


class ProfessionalContextClassifier(BaseClassifier):
    """Detects unprofessional content in business contexts."""
    
    def __init__(self, threshold: float = 0.5):
        super().__init__("professional_context", threshold)
        
        # Unprofessional patterns
        self.unprofessional_patterns = [
            r'\b(lol|lmao|wtf|omg|brb)\b',
            r'\b(dude|bro|guys)\b',
            r'\b(whatever|meh|yolo)\b',
            r'!!!+',  # Excessive exclamation
            r'\?\?\?+',  # Excessive question marks
        ]
    
    async def classify(self, text: str) -> Dict[str, Any]:
        """Detect unprofessional content."""
        text_lower = text.lower()
        violations = []
        
        for pattern in self.unprofessional_patterns:
            matches = re.findall(pattern, text_lower)
            if matches:
                violations.extend(matches)
        
        score = min(len(violations) * 0.2, 1.0)
        flagged = score >= self.threshold
        
        return {
            "score": score,
            "flagged": flagged,
            "details": {
                "violation_count": len(violations),
                "examples": violations[:5],
            },
            "category": "unprofessional",
        }


class ComplianceClassifier(BaseClassifier):
    """Detects potential compliance violations (HIPAA, GDPR, etc.)."""
    
    def __init__(self, threshold: float = 0.7):
        super().__init__("compliance", threshold)
        
        # Medical/health terms (HIPAA)
        self.medical_terms = [
            r'\b(patient|diagnosis|prescription|medical record)\b',
            r'\b(blood pressure|medication|surgery|treatment)\b',
            r'\b(doctor|hospital|clinic)\b',
        ]
        
        # Legal terms
        self.legal_terms = [
            r'\b(confidential|privileged|attorney-client)\b',
            r'\b(contract|agreement|settlement)\b',
        ]
    
    async def classify(self, text: str) -> Dict[str, Any]:
        """Detect compliance-sensitive content."""
        text_lower = text.lower()
        medical_count = 0
        legal_count = 0
        
        for pattern in self.medical_terms:
            if re.search(pattern, text_lower):
                medical_count += 1
        
        for pattern in self.legal_terms:
            if re.search(pattern, text_lower):
                legal_count += 1
        
        # High score if contains both PII and sensitive terms
        score = min((medical_count + legal_count) * 0.15, 1.0)
        flagged = score >= self.threshold
        
        return {
            "score": score,
            "flagged": flagged,
            "details": {
                "medical_terms": medical_count,
                "legal_terms": legal_count,
                "risk_level": "high" if score > 0.7 else "medium" if score > 0.4 else "low",
            },
            "category": "compliance",
        }


class ClassifierRegistry:
    """Registry for managing custom classifiers."""
    
    def __init__(self):
        self._classifiers: Dict[str, BaseClassifier] = {}
        self._initialize_default_classifiers()
    
    def _initialize_default_classifiers(self):
        """Register default classifiers."""
        self.register(PIIDetector())
        self.register(MisinformationDetector())
        self.register(ProfessionalContextClassifier())
        self.register(ComplianceClassifier())
    
    def register(self, classifier: BaseClassifier):
        """Register a custom classifier."""
        self._classifiers[classifier.name] = classifier
    
    def unregister(self, name: str):
        """Unregister a classifier."""
        if name in self._classifiers:
            del self._classifiers[name]
    
    def get(self, name: str) -> Optional[BaseClassifier]:
        """Get classifier by name."""
        return self._classifiers.get(name)
    
    def list_classifiers(self) -> List[str]:
        """List all registered classifiers."""
        return list(self._classifiers.keys())
    
    async def classify_all(self, text: str, enabled_classifiers: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Run all enabled classifiers on text.
        
        Args:
            text: Text to classify
            enabled_classifiers: List of classifier names to run (None = all)
            
        Returns:
            Dict with results from all classifiers
        """
        results = {}
        
        classifiers_to_run = enabled_classifiers or list(self._classifiers.keys())
        
        for name in classifiers_to_run:
            classifier = self._classifiers.get(name)
            if classifier:
                results[name] = await classifier.classify(text)
        
        # Compute overall score
        scores = [r["score"] for r in results.values() if "score" in r]
        overall_score = max(scores) if scores else 0.0
        
        # Check if any flagged
        any_flagged = any(r.get("flagged", False) for r in results.values())
        
        return {
            "overall_score": overall_score,
            "flagged": any_flagged,
            "classifier_results": results,
        }


# Global registry instance
classifier_registry = ClassifierRegistry()
