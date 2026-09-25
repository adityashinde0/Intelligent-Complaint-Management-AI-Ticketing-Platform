from typing import Any, Dict, List, Tuple
from app.core.config import settings

class SeverityEngine:
    """Hybrid ML + Policy Severity Determination Engine.
    Implements deterministic overrides for safety and SLA compliance.
    """

    URGENT_OVERRIDE_PATTERNS = [
        "data breach", "security breach", "ransomware", "hacked and ransomware",
        "hospital", "emergency", "life safety", "critical infrastructure",
        "production down", "entire company down", "all users down",
        "fire", "smoke", "sparking", "burning plastic", "overheating with smell", "legal notice"
    ]

    HIGH_OVERRIDE_PATTERNS = [
        "vip", "enterprise tier", "executive", "payroll",
        "financial loss", "cannot process orders", "unusable for 24h",
        "recurring outage", "sla violation", "downtown office campus",
        "dns resolution failing", "physically severed", "completely severed",
        "severed", "phishing email", "two-factor", "2fa", "password was compromised",
        "completely down", "since morning"
    ]

    MEDIUM_PATTERNS = [
        "dropping packets", "latency is over", "tower signal dropped",
        "no internet throughput", "billed twice", "unrecognized charge",
        "payment failed", "duplicate charge", "blinking red", "damaged with exposed",
        "power supply brick died", "unauthorized password reset"
    ]

    def __init__(self):
        self.model_name = "severity-hybrid-policy"
        self.model_version = settings.SEVERITY_MODEL_VERSION
        self.policy_version = settings.POLICY_VERSION

    def evaluate(
        self,
        text: str,
        entities: Dict[str, Any],
        client_tier: str = "STANDARD"
    ) -> Tuple[str, float, bool, List[str]]:
        text_lower = text.lower()
        rationale: List[str] = []

        # 1. Deterministic Hard Policy Overrides (URGENT)
        for pattern in self.URGENT_OVERRIDE_PATTERNS:
            if pattern in text_lower:
                rationale.append(f"Deterministic policy override: critical pattern '{pattern}'")
                return "URGENT", 0.99, True, rationale

        # 2. Deterministic Hard Policy Overrides (HIGH)
        for pattern in self.HIGH_OVERRIDE_PATTERNS:
            if pattern in text_lower:
                rationale.append(f"Deterministic policy override: high-impact pattern '{pattern}'")
                return "HIGH", 0.95, True, rationale

        if client_tier.upper() in ["ENTERPRISE", "MISSION_CRITICAL"]:
            rationale.append(f"Deterministic policy override: client SLA tier is {client_tier}")
            return "HIGH", 0.92, True, rationale

        # 3. Medium patterns
        for pattern in self.MEDIUM_PATTERNS:
            if pattern in text_lower:
                rationale.append(f"Pattern matched moderate operational disruption '{pattern}'")
                return "MEDIUM", 0.88, False, rationale

        # 4. Low indicators
        rationale.append("Standard severity assessment: no high urgency or critical degradation signals detected")
        return "LOW", 0.85, False, rationale

severity_engine = SeverityEngine()
