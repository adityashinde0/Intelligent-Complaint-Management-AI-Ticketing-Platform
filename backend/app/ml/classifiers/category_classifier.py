import math
from typing import Any, Dict, List, Tuple
from uuid import UUID
from app.core.config import settings
from app.core.database import db

class CategoryClassifier:
    """Predicts category using feature scoring and softmax normalization."""

    CATEGORY_WEIGHTS = {
        "General Inquiry": {
            "keywords": ["hours", "operating hours", "procedure", "instructions", "where can i", "terms of service", "upgrading", "how do i", "contact", "support call center"],
            "boost": 2.5
        },
        "Account Security": {
            "keywords": ["data breach", "security breach", "ransomware", "hacked", "phishing", "compromised", "two-factor", "2fa", "unauthorized", "password reset", "credentials"],
            "boost": 3.0
        },
        "Billing Discrepancy": {
            "keywords": ["billed", "charge", "refund", "invoice", "overcharged", "subscription", "payment", "auto-debit", "statement", "dispute", "disputed", "promotional credit", "penalty", "credit card"],
            "boost": 2.5
        },
        "Hardware Malfunction": {
            "keywords": ["power supply", "adapter", "smoking", "sparking", "wan light", "blinking red", "ethernet port", "power button", "cable", "wiring", "overheating", "burning plastic", "brick died", "coaxial connector", "hardware"],
            "boost": 2.5
        },
        "Network Outage": {
            "keywords": ["broadband", "down", "internet", "wifi", "fiber", "packets", "packet loss", "ping", "latency", "dns", "signal dropped", "throughput", "offline", "outage"],
            "boost": 2.0
        }
    }

    def __init__(self):
        self.model_name = "category-hierarchical-softmax"
        self.model_version = settings.CATEGORY_MODEL_VERSION

    def predict(self, text: str) -> Tuple[UUID, str, float, Dict[str, float]]:
        text_lower = text.lower()
        logits: Dict[str, float] = {}

        # First check specific inquiry intent patterns
        is_inquiry_starter = any(text_lower.startswith(p) for p in ["how do i", "where can i", "what are your", "looking for the", "interested in"])
        
        for cat_name, config in self.CATEGORY_WEIGHTS.items():
            score = 0.5
            for kw in config["keywords"]:
                if kw in text_lower:
                    score += config["boost"]
            
            # If phrased as general inquiry question and matches general inquiry keywords, boost General Inquiry
            if cat_name == "General Inquiry" and is_inquiry_starter:
                score += 3.0

            logits[cat_name] = score

        # Softmax computation
        max_logit = max(logits.values())
        exp_logits = {k: math.exp(v - max_logit) for k, v in logits.items()}
        sum_exp = sum(exp_logits.values())
        probabilities = {k: round(v / sum_exp, 4) for k, v in exp_logits.items()}

        best_category_name = max(probabilities, key=probabilities.get)
        confidence = probabilities[best_category_name]

        # Match to database category ID
        cat_id = None
        for cid, cat in db.categories.items():
            if cat["name"] == best_category_name:
                cat_id = cid
                break

        if not cat_id:
            cat_id = list(db.categories.keys())[0]

        return cat_id, best_category_name, confidence, probabilities

category_classifier = CategoryClassifier()
