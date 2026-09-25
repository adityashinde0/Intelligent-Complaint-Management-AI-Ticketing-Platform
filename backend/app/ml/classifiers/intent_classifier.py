import re
from typing import Any, Dict, List, Tuple
from app.core.config import settings

class IntentEntityClassifier:
    """Classifies customer message intent and extracts structured entities."""

    INTENTS = {
        "FAQ_QUERY": [
            "how to", "how do i", "instructions", "power-cycle", "what is", "looking for",
            "reset", "password", "refund policy", "hours", "procedure", "guide", "steps", "reboot"
        ],
        "STATUS_CHECK": [
            "status", "check ticket", "update on my", "ticket #", "ticket id", "where is my"
        ],
        "ESCALATION_REQUEST": [
            "speak to human", "manager", "supervisor", "escalate", "lawyer", "unacceptable"
        ],
        "COMPLAINT_INTAKE": [
            "down", "broken", "outage", "slow", "error", "charged", "billing", "not working",
            "cut", "failure", "severed"
        ]
    }

    ENTITY_PATTERNS = {
        "account_id": r"(?:acct|account|acc)[\s#:]*([A-Za-z0-9\-_]{4,12})",
        "ticket_id": r"(?:ticket|case)[\s#:]*([a-f0-9\-]{8,36})",
        "phone_number": r"(\+?[0-9]{1,3}?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4})",
        "error_code": r"\b(ERR[-_]?[0-9]{3,5}|PON[-_]?[A-Z0-9]+|HTTP[-_]?[0-9]{3}|STATUS[-_]?[0-9]{3})\b",
        "dollar_amount": r"(\$[0-9]+(?:\.[0-9]{2})?|\b[0-9]+\s*(?:dollars|usd)\b)"
    }

    def __init__(self):
        self.model_name = "intent-entity-regex-fast"
        self.model_version = settings.INTENT_MODEL_VERSION

    def normalize_text(self, text: str) -> str:
        text = text.strip()
        text = re.sub(r"\s+", " ", text)
        return text

    def extract_entities(self, text: str) -> Dict[str, Any]:
        entities: Dict[str, Any] = {}
        for entity_name, pattern in self.ENTITY_PATTERNS.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                entities[entity_name] = matches[0] if len(matches) == 1 else matches
        return entities

    def classify_intent(self, text: str) -> Tuple[str, float]:
        norm = text.lower()
        
        # Check escalation first
        for kw in self.INTENTS["ESCALATION_REQUEST"]:
            if kw in norm:
                return "ESCALATION_REQUEST", 0.96

        # Check status check
        for kw in self.INTENTS["STATUS_CHECK"]:
            if kw in norm:
                return "STATUS_CHECK", 0.94

        # Check FAQ query
        faq_score = sum(1 for kw in self.INTENTS["FAQ_QUERY"] if kw in norm)
        complaint_score = sum(1 for kw in self.INTENTS["COMPLAINT_INTAKE"] if kw in norm)

        if faq_score > 0 and (complaint_score == 0 or any(norm.startswith(p) for p in ["how do i", "how to", "what is", "looking for"])):
            return "FAQ_QUERY", min(0.85 + (0.04 * faq_score), 0.98)

        if complaint_score > 0:
            return "COMPLAINT_INTAKE", min(0.80 + (0.04 * complaint_score), 0.99)

        # Generic default
        return "COMPLAINT_INTAKE", 0.70

intent_classifier = IntentEntityClassifier()
