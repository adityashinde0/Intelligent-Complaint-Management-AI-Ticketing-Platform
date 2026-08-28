from pydantic import BaseModel, constr, confloat
from typing import Literal, Optional, List
from uuid import UUID

class ConversationMessage(BaseModel):
    conversation_id: Optional[UUID] = None
    text: constr(min_length=1, max_length=8000)
    language: Optional[str] = None
    client_message_id: UUID

class AIDecision(BaseModel):
    decision_type: Literal[
        "intent", "category", "severity", "routing", "retrieval", "response"
    ]
    value: dict
    confidence: confloat(ge=0.0, le=1.0)
    model_name: str
    model_version: str
    policy_version: str
    evidence_ids: List[UUID] = []

class TicketCreate(BaseModel):
    complaint_text: constr(min_length=1, max_length=20000)
    category_id: UUID
    severity: Literal["LOW", "MEDIUM", "HIGH", "URGENT"]
    source: Literal["CHATBOT", "WEB", "AGENT", "API"]
    extracted_entities: dict
    ai_decision_id: Optional[UUID] = None

class AssignmentRecommendation(BaseModel):
    team_id: UUID
    agent_id: Optional[UUID] = None
    score: confloat(ge=0.0, le=1.0)
    hard_constraints_satisfied: bool
    rationale: List[str]
    model_version: str
