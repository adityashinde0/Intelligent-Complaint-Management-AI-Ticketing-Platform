import json
from typing import Any, Dict, List
from app.ml.classifiers.category_classifier import category_classifier
from app.ml.classifiers.severity_engine import severity_engine
from app.services.rag_service import rag_service

# Static Ground-Truth Benchmark Dataset for rigorous testing
BENCHMARK_CASES = [
    # Network Outages
    {"text": "Fiber broadband is completely down in zip code 90210 since morning.", "category": "Network Outage", "severity": "HIGH"},
    {"text": "Wi-Fi keeps dropping packets, ping latency is over 500ms.", "category": "Network Outage", "severity": "MEDIUM"},
    {"text": "Total internet loss across our whole downtown office campus.", "category": "Network Outage", "severity": "HIGH"},
    {"text": "Our fiber connection was physically severed by construction workers.", "category": "Network Outage", "severity": "HIGH"},
    {"text": "Minor intermittent slow internet during peak evening streaming.", "category": "Network Outage", "severity": "LOW"},
    {"text": "Entire production down, all users down across headquarters!", "category": "Network Outage", "severity": "URGENT"},
    {"text": "DNS resolution failing across our corporate domain.", "category": "Network Outage", "severity": "HIGH"},
    {"text": "Cellular broadband tower signal dropped to zero bars.", "category": "Network Outage", "severity": "MEDIUM"},
    {"text": "Modem lights are green but no internet throughput at all.", "category": "Network Outage", "severity": "MEDIUM"},
    {"text": "Critical hospital telemetry network connection severed!", "category": "Network Outage", "severity": "URGENT"},

    # Billing Discrepancies
    {"text": "I was billed twice for last month's enterprise subscription.", "category": "Billing Discrepancy", "severity": "MEDIUM"},
    {"text": "Unrecognized charge of $450 on my credit card statement.", "category": "Billing Discrepancy", "severity": "MEDIUM"},
    {"text": "Need a refund for the period when internet service was offline.", "category": "Billing Discrepancy", "severity": "LOW"},
    {"text": "Overcharged invoice fee for hardware that was returned months ago.", "category": "Billing Discrepancy", "severity": "LOW"},
    {"text": "Corporate invoice payment failed due to system billing glitch.", "category": "Billing Discrepancy", "severity": "MEDIUM"},
    {"text": "Financial loss incurred due to incorrect recurring auto-debit of $10,000.", "category": "Billing Discrepancy", "severity": "HIGH"},
    {"text": "Contractual billing rate dispute on enterprise tier SLA agreement.", "category": "Billing Discrepancy", "severity": "HIGH"},
    {"text": "Invoice item shows unexpected cancellation penalty.", "category": "Billing Discrepancy", "severity": "LOW"},
    {"text": "Please provide an updated statement showing the applied promotional credit.", "category": "Billing Discrepancy", "severity": "LOW"},
    {"text": "Duplicate charge on account statement for March.", "category": "Billing Discrepancy", "severity": "MEDIUM"},

    # Hardware Malfunctions
    {"text": "Router power supply adapter is smoking and sparking at outlet!", "category": "Hardware Malfunction", "severity": "URGENT"},
    {"text": "Optical WAN light on modem is blinking red after thunderstorm.", "category": "Hardware Malfunction", "severity": "MEDIUM"},
    {"text": "Ethernet port 2 on router is physically broken.", "category": "Hardware Malfunction", "severity": "LOW"},
    {"text": "Device power button stuck and refuses to turn on.", "category": "Hardware Malfunction", "severity": "LOW"},
    {"text": "Replacement cable arrived damaged with exposed wiring.", "category": "Hardware Malfunction", "severity": "MEDIUM"},
    {"text": "Router chassis overheating with smell of burning plastic.", "category": "Hardware Malfunction", "severity": "URGENT"},
    {"text": "Modem power supply brick died and has no power indicator.", "category": "Hardware Malfunction", "severity": "MEDIUM"},
    {"text": "Coaxial connector detached from wall terminal box.", "category": "Hardware Malfunction", "severity": "LOW"},

    # Account Security & Breaches
    {"text": "Security breach detected! Unauthorized credentials login from foreign IP.", "category": "Account Security", "severity": "URGENT"},
    {"text": "Our corporate database administrator account was hacked and ransomware deployed.", "category": "Account Security", "severity": "URGENT"},
    {"text": "Received a phishing email and my password was compromised.", "category": "Account Security", "severity": "HIGH"},
    {"text": "Unauthorized password reset requested on my account.", "category": "Account Security", "severity": "MEDIUM"},
    {"text": "Data breach notification: customer credit card records potentially exposed.", "category": "Account Security", "severity": "URGENT"},
    {"text": "Someone changed my two-factor authentication phone number without permission.", "category": "Account Security", "severity": "HIGH"},

    # General Inquiries & FAQ
    {"text": "What are your customer support call center operating hours?", "category": "General Inquiry", "severity": "LOW"},
    {"text": "Looking for the standard router reset procedure and instructions.", "category": "General Inquiry", "severity": "LOW"},
    {"text": "Where can I review the enterprise terms of service and refund policy?", "category": "General Inquiry", "severity": "LOW"},
    {"text": "Interested in upgrading to a faster fiber business plan next month.", "category": "General Inquiry", "severity": "LOW"},
    {"text": "How do I request a static IP allocation for my new office?", "category": "General Inquiry", "severity": "LOW"}
]

class AIEvaluationHarness:
    """Computes F1, Recall, Precision and RAG Groundedness metrics."""

    def run_evaluation(self) -> Dict[str, Any]:
        cat_actual, cat_pred = [], []
        sev_actual, sev_pred = [], []

        for case in BENCHMARK_CASES:
            # 1. Category evaluation
            _, pred_cat, _, _ = category_classifier.predict(case["text"])
            cat_actual.append(case["category"])
            cat_pred.append(pred_cat)

            # 2. Severity evaluation
            pred_sev, _, _, _ = severity_engine.evaluate(case["text"], {})
            sev_actual.append(case["severity"])
            sev_pred.append(pred_sev)

        # Compute Metrics
        cat_macro_f1 = self._compute_macro_f1(cat_actual, cat_pred)
        sev_macro_f1 = self._compute_macro_f1(sev_actual, sev_pred)
        urgent_recall = self._compute_class_recall(sev_actual, sev_pred, "URGENT")
        high_recall = self._compute_class_recall(sev_actual, sev_pred, "HIGH")

        # 3. RAG Retrieval & Grounding Evaluation
        rag_queries = [
            ("How do I power-cycle my router?", "power-cycle"),
            ("What is your refund policy for disputed charges?", "disputed")
        ]
        grounded_count = 0
        retrieval_success_count = 0

        for query, expected_keyword in rag_queries:
            chunks = rag_service.retrieve(query, top_k=5)
            if any(expected_keyword in (c["content"] + " " + c.get("document_title", "")).lower() for c in chunks):
                retrieval_success_count += 1
            
            ans, _, source_chunks = rag_service.answer_query(query)
            if ans:
                is_grounded, _ = rag_service.validate_grounding(ans, source_chunks)
                if is_grounded:
                    grounded_count += 1

        retrieval_recall = retrieval_success_count / len(rag_queries)
        groundedness = grounded_count / len(rag_queries)
        unsupported_rate = 1.0 - groundedness

        results = {
            "category_macro_f1": round(cat_macro_f1, 4),
            "severity_macro_f1": round(sev_macro_f1, 4),
            "urgent_recall": round(urgent_recall, 4),
            "high_severity_recall": round(high_recall, 4),
            "retrieval_recall_at_5": round(retrieval_recall, 4),
            "groundedness": round(groundedness, 4),
            "unsupported_answer_rate": round(unsupported_rate, 4),
            "total_benchmark_cases": len(BENCHMARK_CASES)
        }

        # Validate against targets in AI_EVALUATION.md
        results["targets_satisfied"] = (
            results["category_macro_f1"] >= 0.90 and
            results["severity_macro_f1"] >= 0.88 and
            results["urgent_recall"] >= 0.95 and
            results["high_severity_recall"] >= 0.90 and
            results["retrieval_recall_at_5"] >= 0.95 and
            results["groundedness"] >= 0.98 and
            results["unsupported_answer_rate"] <= 0.01
        )

        return results

    def _compute_macro_f1(self, actual: List[str], predicted: List[str]) -> float:
        classes = list(set(actual))
        f1_scores = []
        for cls in classes:
            tp = sum(1 for a, p in zip(actual, predicted) if a == cls and p == cls)
            fp = sum(1 for a, p in zip(actual, predicted) if a != cls and p == cls)
            fn = sum(1 for a, p in zip(actual, predicted) if a == cls and p != cls)
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
            f1_scores.append(f1)
        return sum(f1_scores) / len(f1_scores) if f1_scores else 0.0

    def _compute_class_recall(self, actual: List[str], predicted: List[str], target_cls: str) -> float:
        tp = sum(1 for a, p in zip(actual, predicted) if a == target_cls and p == target_cls)
        fn = sum(1 for a, p in zip(actual, predicted) if a == target_cls and p != target_cls)
        return tp / (tp + fn) if (tp + fn) > 0 else 1.0

evaluation_harness = AIEvaluationHarness()

if __name__ == "__main__":
    report = evaluation_harness.run_evaluation()
    print(json.dumps(report, indent=2))
