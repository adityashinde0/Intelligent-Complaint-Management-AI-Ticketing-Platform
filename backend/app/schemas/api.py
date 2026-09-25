from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, constr, confloat


# --- Identity & Auth Schemas ---
UserRole = Literal["customer", "agent", "admin"]

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    email: str
    role: UserRole
    status: str
    created_at: datetime

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# --- Conversation & Chat Schemas ---
class ConversationCreate(BaseModel):
    user_id: Optional[UUID] = None
    language: Optional[str] = "en"
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class ConversationMessage(BaseModel):
    conversation_id: Optional[UUID] = None
    text: constr(min_length=1, max_length=8000)
    language: Optional[str] = "en"
    client_message_id: UUID = Field(default_factory=uuid4)

class MessageResponse(BaseModel):
    status: Literal["success", "clarifying", "escalated_to_ticket"]
    message_id: UUID
    conversation_id: UUID
    response: str
    confidence: confloat(ge=0.0, le=1.0)
    intent: str
    suggested_actions: List[str] = Field(default_factory=list)
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    ticket_id: Optional[UUID] = None


# --- AI Decisions & Grounding Schemas ---
DecisionType = Literal[
    "intent", "category", "severity", "routing", "retrieval", "response"
]

class AIDecision(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    ticket_id: Optional[UUID] = None
    decision_type: DecisionType
    value: Dict[str, Any]
    confidence: confloat(ge=0.0, le=1.0)
    model_name: str
    model_version: str
    policy_version: str
    evidence_ids: List[UUID] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AIEvidence(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    ai_decision_id: UUID
    knowledge_chunk_id: UUID
    document_title: str
    similarity_score: confloat(ge=0.0, le=1.0)
    rank: int
    metadata: Dict[str, Any] = Field(default_factory=dict)


# --- Ticket Schemas ---
TicketSeverity = Literal["LOW", "MEDIUM", "HIGH", "URGENT"]
TicketStatus = Literal["OPEN", "IN_PROGRESS", "ESCALATED", "RESOLVED", "CLOSED"]
TicketSource = Literal["CHATBOT", "WEB", "AGENT", "API"]

class TicketCreate(BaseModel):
    complaint_text: constr(min_length=1, max_length=20000)
    category_id: Optional[UUID] = None
    severity: Optional[TicketSeverity] = None
    source: TicketSource = "WEB"
    extracted_entities: Dict[str, Any] = Field(default_factory=dict)
    ai_decision_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    client_idempotency_key: Optional[str] = None

class TicketUpdate(BaseModel):
    status: Optional[TicketStatus] = None
    severity: Optional[TicketSeverity] = None
    assigned_agent_id: Optional[UUID] = None
    team_id: Optional[UUID] = None
    version: int

class TicketAssignRequest(BaseModel):
    agent_id: UUID
    team_id: Optional[UUID] = None
    rationale: Optional[str] = None
    version: int

class TicketEscalateRequest(BaseModel):
    reason: str
    target_tier: Optional[str] = "Tier-2"
    version: int

class TicketResolveRequest(BaseModel):
    resolution_notes: str
    resolution_code: str = "RESOLVED_VERIFIED"
    version: int

class TicketEventResponse(BaseModel):
    id: UUID
    ticket_id: UUID
    event_type: str
    actor_type: str
    actor_id: Optional[UUID] = None
    payload: Dict[str, Any]
    created_at: datetime

class TicketResponse(BaseModel):
    id: UUID
    complaint_id: UUID
    complaint_text: str
    category_id: Optional[UUID] = None
    category_name: Optional[str] = None
    severity: TicketSeverity
    status: TicketStatus
    team_id: Optional[UUID] = None
    team_name: Optional[str] = None
    assigned_agent_id: Optional[UUID] = None
    assigned_agent_name: Optional[str] = None
    sla_due_at: Optional[datetime] = None
    sla_status: Optional[str] = "ON_TRACK"
    resolved_at: Optional[datetime] = None
    version: int
    created_at: datetime
    updated_at: datetime
    ai_decisions: List[AIDecision] = Field(default_factory=list)


# --- Routing & Assignment Schemas ---
class AssignmentRecommendation(BaseModel):
    team_id: UUID
    team_name: str
    agent_id: Optional[UUID] = None
    agent_name: Optional[str] = None
    score: confloat(ge=0.0, le=1.0)
    hard_constraints_satisfied: bool
    rationale: List[str]
    model_version: str

class AgentQueueItem(BaseModel):
    ticket_id: UUID
    severity: TicketSeverity
    status: TicketStatus
    category_name: str
    complaint_summary: str
    sla_due_at: datetime
    sla_remaining_minutes: int
    created_at: datetime


# --- Analytics & Admin Schemas ---
class AnalyticsOverview(BaseModel):
    open_tickets: int
    sla_breach_rate: float
    mean_resolution_time: str
    ai_automation_rate: float
    human_override_rate: float
    severity_distribution: Dict[str, int]
    category_distribution: Dict[str, int]
    active_escalations: int

class ModelMetadata(BaseModel):
    model_name: str
    version: str
    task: str
    accuracy_metric: str
    metric_value: float
    status: str
    promoted_at: datetime

class PolicyConfig(BaseModel):
    policy_version: str
    sla_urgent_hours: int
    sla_high_hours: int
    sla_medium_hours: int
    sla_low_hours: int
    rag_confidence_threshold: float
    human_triage_confidence_threshold: float
    auto_escalation_enabled: bool


# --- RFC 7807 Problem Detail ---
class ProblemDetail(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    detail: str
    instance: Optional[str] = None
    invalid_params: Optional[List[Dict[str, Any]]] = None
