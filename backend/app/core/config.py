import os
from pydantic import BaseModel

class Settings(BaseModel):
    PROJECT_NAME: str = "Intelligent Complaint Management & AI Ticketing Platform"
    API_V1_STR: str = "/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-jwt-key-anti-gravity-2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # AI & Model Versions
    INTENT_MODEL_VERSION: str = "intent-clf-v2.1"
    CATEGORY_MODEL_VERSION: str = "category-hier-v3.0"
    SEVERITY_MODEL_VERSION: str = "severity-hybrid-v2.4"
    ROUTING_MODEL_VERSION: str = "assignment-rank-v1.8"
    EMBEDDING_MODEL_VERSION: str = "text-embedding-004-v1"
    POLICY_VERSION: str = "enterprise-policy-2026.09"

    # Operational Gates & Thresholds
    RAG_CONFIDENCE_THRESHOLD: float = 0.85
    GROUNDING_THRESHOLD: float = 0.95
    CATEGORY_CONFIDENCE_THRESHOLD: float = 0.75
    SEVERITY_CONFIDENCE_THRESHOLD: float = 0.80

    # SLAs (Hours)
    SLA_URGENT_HOURS: int = 1
    SLA_HIGH_HOURS: int = 4
    SLA_MEDIUM_HOURS: int = 24
    SLA_LOW_HOURS: int = 72

settings = Settings()
