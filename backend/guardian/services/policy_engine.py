"""
Policy Engine - Per-tenant custom safety rules.

Allows organizations to define their own safety policies beyond
standard toxicity/bias checks.
"""

import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class PolicyAction(str, Enum):
    """Action to take when policy is violated."""
    BLOCK = "block"
    WARN = "warn"
    REDACT = "redact"
    LOG_ONLY = "log_only"


class PolicySeverity(str, Enum):
    """Severity level of policy violation."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class PolicyRule:
    """Individual policy rule."""
    
    id: str
    name: str
    description: str
    pattern: str  # Regex pattern
    action: PolicyAction
    severity: PolicySeverity
    enabled: bool = True
    case_sensitive: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def matches(self, text: str) -> bool:
        """Check if text matches this rule."""
        flags = 0 if self.case_sensitive else re.IGNORECASE
        return bool(re.search(self.pattern, text, flags))
    
    def find_matches(self, text: str) -> List[Dict[str, Any]]:
        """Find all matches with positions."""
        flags = 0 if self.case_sensitive else re.IGNORECASE
        matches = []
        
        for match in re.finditer(self.pattern, text, flags):
            matches.append({
                "text": match.group(),
                "start": match.start(),
                "end": match.end(),
                "groups": match.groups(),
            })
        
        return matches


@dataclass
class TenantPolicy:
    """Complete policy configuration for a tenant."""
    
    tenant_id: str
    name: str
    description: str
    rules: List[PolicyRule] = field(default_factory=list)
    enabled: bool = True
    
    # Thresholds
    toxicity_threshold: float = 0.7
    bias_threshold: float = 0.3
    pii_threshold: float = 0.8
    
    # Feature flags
    enable_toxicity: bool = True
    enable_bias: bool = True
    enable_jailbreak: bool = True
    enable_pii: bool = True
    enable_custom_classifiers: bool = True
    
    # Allowed/blocked lists
    allowed_domains: List[str] = field(default_factory=list)
    blocked_keywords: List[str] = field(default_factory=list)
    
    def add_rule(self, rule: PolicyRule):
        """Add a rule to this policy."""
        self.rules.append(rule)
    
    def remove_rule(self, rule_id: str):
        """Remove a rule by ID."""
        self.rules = [r for r in self.rules if r.id != rule_id]
    
    def get_rule(self, rule_id: str) -> Optional[PolicyRule]:
        """Get rule by ID."""
        for rule in self.rules:
            if rule.id == rule_id:
                return rule
        return None
    
    def evaluate(self, text: str) -> Dict[str, Any]:
        """
        Evaluate text against all policy rules.
        
        Returns:
            Dict with violations and recommended actions
        """
        violations = []
        
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            matches = rule.find_matches(text)
            if matches:
                violations.append({
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "severity": rule.severity,
                    "action": rule.action,
                    "matches": matches,
                    "description": rule.description,
                })
        
        # Determine overall action
        if not violations:
            overall_action = PolicyAction.LOG_ONLY
            max_severity = PolicySeverity.LOW
        else:
            # Take the most severe action
            action_priority = {
                PolicyAction.BLOCK: 4,
                PolicyAction.REDACT: 3,
                PolicyAction.WARN: 2,
                PolicyAction.LOG_ONLY: 1,
            }
            
            overall_action = max(
                (v["action"] for v in violations),
                key=lambda a: action_priority[a]
            )
            
            severity_priority = {
                PolicySeverity.CRITICAL: 4,
                PolicySeverity.HIGH: 3,
                PolicySeverity.MEDIUM: 2,
                PolicySeverity.LOW: 1,
            }
            
            max_severity = max(
                (v["severity"] for v in violations),
                key=lambda s: severity_priority[s]
            )
        
        return {
            "violations": violations,
            "violation_count": len(violations),
            "overall_action": overall_action,
            "max_severity": max_severity,
            "policy_name": self.name,
        }


class PolicyEngine:
    """Manages and evaluates policies for all tenants."""
    
    def __init__(self):
        self._policies: Dict[str, TenantPolicy] = {}
        self._initialize_default_policies()
    
    def _initialize_default_policies(self):
        """Create default policies for demonstration."""
        
        # Healthcare policy (HIPAA compliant)
        healthcare_policy = TenantPolicy(
            tenant_id="healthcare_demo",
            name="Healthcare HIPAA Policy",
            description="Strict policy for healthcare data",
            enable_pii=True,
            pii_threshold=0.5,  # Lower threshold = stricter
        )
        
        healthcare_policy.add_rule(PolicyRule(
            id="hipaa_phi",
            name="Protected Health Information",
            description="Detects PHI mentions",
            pattern=r'\b(patient\s+\w+|diagnosis|medical\s+record|health\s+insurance)\b',
            action=PolicyAction.BLOCK,
            severity=PolicySeverity.CRITICAL,
        ))
        
        healthcare_policy.add_rule(PolicyRule(
            id="prescription_info",
            name="Prescription Information",
            description="Detects prescription details",
            pattern=r'\b(prescription|medication|dosage|mg|pill)\b',
            action=PolicyAction.REDACT,
            severity=PolicySeverity.HIGH,
        ))
        
        self._policies["healthcare_demo"] = healthcare_policy
        
        # Corporate policy
        corporate_policy = TenantPolicy(
            tenant_id="corporate_demo",
            name="Corporate Communications Policy",
            description="Professional communication standards",
        )
        
        corporate_policy.add_rule(PolicyRule(
            id="confidential",
            name="Confidential Information",
            description="Flags confidential/proprietary content",
            pattern=r'\b(confidential|proprietary|trade\s+secret|internal\s+only)\b',
            action=PolicyAction.WARN,
            severity=PolicySeverity.HIGH,
        ))
        
        corporate_policy.add_rule(PolicyRule(
            id="profanity",
            name="Professional Language",
            description="Blocks profanity in corporate comms",
            pattern=r'\b(fuck|shit|damn|hell)\b',
            action=PolicyAction.BLOCK,
            severity=PolicySeverity.MEDIUM,
        ))
        
        corporate_policy.add_rule(PolicyRule(
            id="competitor_mention",
            name="Competitor Mentions",
            description="Logs competitor references",
            pattern=r'\b(competitor|rival\s+company)\b',
            action=PolicyAction.LOG_ONLY,
            severity=PolicySeverity.LOW,
        ))
        
        self._policies["corporate_demo"] = corporate_policy
        
        # Financial services policy
        finance_policy = TenantPolicy(
            tenant_id="finance_demo",
            name="Financial Services Compliance",
            description="SEC and FINRA compliance rules",
        )
        
        finance_policy.add_rule(PolicyRule(
            id="investment_advice",
            name="Unauthorized Investment Advice",
            description="Flags potential unlicensed advice",
            pattern=r'\b(guaranteed\s+returns|get\s+rich|insider\s+tip)\b',
            action=PolicyAction.BLOCK,
            severity=PolicySeverity.CRITICAL,
        ))
        
        finance_policy.add_rule(PolicyRule(
            id="financial_pii",
            name="Financial PII",
            description="Account numbers, routing numbers",
            pattern=r'\b(account\s+number|routing\s+number|bank\s+account)\b',
            action=PolicyAction.REDACT,
            severity=PolicySeverity.CRITICAL,
        ))
        
        self._policies["finance_demo"] = finance_policy
    
    def register_policy(self, policy: TenantPolicy):
        """Register a new tenant policy."""
        self._policies[policy.tenant_id] = policy
    
    def get_policy(self, tenant_id: str) -> Optional[TenantPolicy]:
        """Get policy for tenant."""
        return self._policies.get(tenant_id)
    
    def evaluate_policy(self, tenant_id: str, text: str) -> Dict[str, Any]:
        """
        Evaluate text against tenant's policy.
        
        Args:
            tenant_id: Tenant identifier
            text: Text to evaluate
            
        Returns:
            Policy evaluation results
        """
        policy = self.get_policy(tenant_id)
        
        if not policy or not policy.enabled:
            return {
                "violations": [],
                "violation_count": 0,
                "overall_action": PolicyAction.LOG_ONLY,
                "max_severity": PolicySeverity.LOW,
                "policy_name": "default",
            }
        
        return policy.evaluate(text)
    
    def create_custom_policy(
        self,
        tenant_id: str,
        name: str,
        description: str,
        rules: List[Dict[str, Any]],
    ) -> TenantPolicy:
        """
        Create a custom policy from configuration.
        
        Args:
            tenant_id: Tenant ID
            name: Policy name
            description: Policy description
            rules: List of rule configurations
            
        Returns:
            Created TenantPolicy
        """
        policy = TenantPolicy(
            tenant_id=tenant_id,
            name=name,
            description=description,
        )
        
        for rule_config in rules:
            rule = PolicyRule(
                id=rule_config["id"],
                name=rule_config["name"],
                description=rule_config.get("description", ""),
                pattern=rule_config["pattern"],
                action=PolicyAction(rule_config.get("action", "warn")),
                severity=PolicySeverity(rule_config.get("severity", "medium")),
                enabled=rule_config.get("enabled", True),
                case_sensitive=rule_config.get("case_sensitive", False),
                metadata=rule_config.get("metadata", {}),
            )
            policy.add_rule(rule)
        
        self.register_policy(policy)
        return policy


# Global policy engine instance
policy_engine = PolicyEngine()
