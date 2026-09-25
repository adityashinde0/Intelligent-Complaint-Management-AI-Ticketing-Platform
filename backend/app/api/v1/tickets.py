from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from app.core.auth import get_current_user, require_role
from app.core.database import db
from app.services.ticket_service import ticket_service
from app.schemas.api import (
    TicketAssignRequest,
    TicketCreate,
    TicketEscalateRequest,
    TicketEventResponse,
    TicketResolveRequest,
    TicketResponse,
    UserResponse
)

router = APIRouter(prefix="/tickets", tags=["Tickets"])

@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    ticket: TicketCreate,
    x_idempotency_key: Optional[str] = Header(None),
    current_user: UserResponse = Depends(get_current_user)
):
    if x_idempotency_key and not ticket.client_idempotency_key:
        ticket.client_idempotency_key = x_idempotency_key
    return ticket_service.create_ticket_transactional(ticket, actor_id=current_user.id)

@router.get("", response_model=List[TicketResponse])
async def list_tickets(
    status_filter: Optional[str] = Query(None, alias="status"),
    severity_filter: Optional[str] = Query(None, alias="severity"),
    team_id: Optional[UUID] = Query(None),
    current_user: UserResponse = Depends(get_current_user)
):
    tickets_out = []
    for tid in db.tickets.keys():
        t_res = ticket_service.get_ticket_by_id(tid)
        if status_filter and t_res.status != status_filter.upper():
            continue
        if severity_filter and t_res.severity != severity_filter.upper():
            continue
        if team_id and t_res.team_id != team_id:
            continue
        tickets_out.append(t_res)
    return tickets_out

@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: UUID,
    current_user: UserResponse = Depends(get_current_user)
):
    return ticket_service.get_ticket_by_id(ticket_id)

@router.get("/{ticket_id}/events", response_model=List[TicketEventResponse])
async def get_ticket_events(
    ticket_id: UUID,
    current_user: UserResponse = Depends(get_current_user)
):
    events = [
        TicketEventResponse(
            id=e["id"],
            ticket_id=e["ticket_id"],
            event_type=e["event_type"],
            actor_type=e["actor_type"],
            actor_id=e["actor_id"],
            payload=e["payload"],
            created_at=e["created_at"]
        )
        for e in db.ticket_events
        if e["ticket_id"] == ticket_id
    ]
    return events

@router.post("/{ticket_id}/assign", response_model=TicketResponse)
async def assign_ticket(
    ticket_id: UUID,
    payload: TicketAssignRequest,
    current_user: UserResponse = Depends(require_role(["agent", "admin"]))
):
    return ticket_service.assign_ticket(
        ticket_id=ticket_id,
        agent_id=payload.agent_id,
        version=payload.version,
        actor_id=current_user.id,
        rationale=payload.rationale
    )

@router.post("/{ticket_id}/escalate", response_model=TicketResponse)
async def escalate_ticket(
    ticket_id: UUID,
    payload: TicketEscalateRequest,
    current_user: UserResponse = Depends(require_role(["agent", "admin"]))
):
    return ticket_service.escalate_ticket(
        ticket_id=ticket_id,
        reason=payload.reason,
        target_tier=payload.target_tier or "Tier-2",
        version=payload.version,
        actor_id=current_user.id
    )

@router.post("/{ticket_id}/resolve", response_model=TicketResponse)
async def resolve_ticket(
    ticket_id: UUID,
    payload: TicketResolveRequest,
    current_user: UserResponse = Depends(require_role(["agent", "admin"]))
):
    return ticket_service.resolve_ticket(
        ticket_id=ticket_id,
        resolution_notes=payload.resolution_notes,
        resolution_code=payload.resolution_code,
        version=payload.version,
        actor_id=current_user.id
    )
