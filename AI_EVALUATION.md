# AI Evaluation Targets

## 1. Classification Targets
- **Category Macro-F1:** >= 0.90
- **Severity Macro-F1:** >= 0.88
- **Urgent Recall:** >= 0.95 (Crucial for minimizing missed escalations)
- **High-Severity Recall:** >= 0.93

## 2. Retrieval & RAG Targets
- **Retrieval Recall@5:** >= 0.95
- **Groundedness:** >= 0.98
- **Unsupported-answer rate:** <= 0.01 (1%)

## 3. Implementation
The evaluation harness will test predictions against a static ground-truth JSON dataset using scikit-learn metrics. Any model failing to meet these targets is marked `NOT VALIDATED`.
