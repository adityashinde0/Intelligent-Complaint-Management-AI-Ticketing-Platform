# Data Leakage Policy

## 1. Temporal Constraints
No model intended for use at `ticket_creation` time may incorporate features that only become available after the complaint has been ingested.
- **Forbidden Features:** Resolution notes, agent comments, assigned team (unless deterministic routing), customer satisfaction scores, later knowledge base articles.

## 2. Feature Availability
All evaluation and training datasets must strictly join data using `feature_available_at <= prediction_timestamp`.

## 3. Human Override Leakage
Human modifications to AI predictions (e.g. changing an AI-predicted severity of `MEDIUM` to `HIGH`) are considered ground truth. The pre-resolution severity feature must use the original AI prediction or the original deterministic policy, not the post-hoc human override, to avoid leaking the answer into subsequent models (like Assignment).

## 4. Train/Test Separation
- Datasets must be split temporally, not randomly.
- A single complaint lineage (including follow-ups or linked cases) must be strictly partitioned into the same split to avoid intra-case leakage.
