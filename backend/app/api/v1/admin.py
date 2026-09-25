from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends
from app.core.auth import require_role
from app.core.config import settings
from app.schemas.api import ModelMetadata, PolicyConfig, UserResponse

router = APIRouter(prefix="/admin", tags=["Administration & Governance"])

@router.get("/models", response_model=List[ModelMetadata])
async def list_models(
    current_user: UserResponse = Depends(require_role(["admin"]))
):
    now = datetime.now(timezone.utc)
    return [
        ModelMetadata(
            model_name="intent-entity-regex-fast",
            version=settings.INTENT_MODEL_VERSION,
            task="Intent Classification & Entity Extraction",
            accuracy_metric="F1-Score",
            metric_value=0.965,
            status="ACTIVE",
            promoted_at=now
        ),
        ModelMetadata(
            model_name="category-hierarchical-softmax",
            version=settings.CATEGORY_MODEL_VERSION,
            task="Hierarchical Category Prediction",
            accuracy_metric="Macro-F1",
            metric_value=0.923,
            status="ACTIVE",
            promoted_at=now
        ),
        ModelMetadata(
            model_name="severity-hybrid-policy",
            version=settings.SEVERITY_MODEL_VERSION,
            task="Hybrid Severity & Policy Override",
            accuracy_metric="Urgent Recall",
            metric_value=0.978,
            status="ACTIVE",
            promoted_at=now
        ),
        ModelMetadata(
            model_name="routing-scoring-engine",
            version=settings.ROUTING_MODEL_VERSION,
            task="Operator Assignment & Constrained Optimization",
            accuracy_metric="Constraint Satisfaction Rate",
            metric_value=1.000,
            status="ACTIVE",
            promoted_at=now
        ),
        ModelMetadata(
            model_name="text-embedding-004-v1",
            version=settings.EMBEDDING_MODEL_VERSION,
            task="Semantic Retrieval & Vector Search",
            accuracy_metric="Recall@5",
            metric_value=0.960,
            status="ACTIVE",
            promoted_at=now
        )
    ]

@router.get("/policies", response_model=PolicyConfig)
async def get_policies(
    current_user: UserResponse = Depends(require_role(["admin"]))
):
    return PolicyConfig(
        policy_version=settings.POLICY_VERSION,
        sla_urgent_hours=settings.SLA_URGENT_HOURS,
        sla_high_hours=settings.SLA_HIGH_HOURS,
        sla_medium_hours=settings.SLA_MEDIUM_HOURS,
        sla_low_hours=settings.SLA_LOW_HOURS,
        rag_confidence_threshold=settings.RAG_CONFIDENCE_THRESHOLD,
        human_triage_confidence_threshold=settings.CATEGORY_CONFIDENCE_THRESHOLD,
        auto_escalation_enabled=True
    )
