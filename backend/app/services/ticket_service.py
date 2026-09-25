from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from app.core.config import settings
from app.core.database import db
from app.core.exceptions import ConflictException, EntityNotFoundException, PolicyViolationException
from app.ml.classifiers.category_classifier import category_classifier
from app.ml.classifiers.intent_classifier import intent_classifier
from app.ml.classifiers.severity_engine import severity_engine
from app.services.audit_service import audit_service
from app.services.outbox_service import outbox_service
from app.services.routing_service import routing_service
from app.services.sla_service import sla_service
from app.schemas.api import AIDecision, TicketCreate, TicketResponse

class TicketService:
    """Core transaction service for Complaint and Ticket lifecycle."""

    def create_ticket_transactional(
        self,
        request: TicketCreate,
        actor_id: Optional[UUID] = None
    ) -> TicketResponse:
        # 1. Idempotency Check (Failure Matrix compliance)
        if request.client_idempotency_key:
            if request.client_idempotency_key in db.idempotency_records:
                cached_id = db.idempotency_records[request.client_idempotency_key]
                return self.get_ticket_by_id(cached_id)

        now = datetime.now(timezone.utc)
        complaint_id = uuid4()
        ticket_id = uuid4()

        # 2. Extract entities & normalize
        normalized_text = intent_classifier.normalize_text(request.complaint_text)
        entities = request.extracted_entities or intent_classifier.extract_entities(normalized_text)

        # 3. AI Intelligence: Category
        if request.category_id and request.category_id in db.categories:
            category_id = request.category_id
            category_name = db.categories[category_id]["name"]
            cat_conf = 1.0
        else:
            category_id, category_name, cat_conf, _ = category_classifier.predict(normalized_text)

        # 4. AI Intelligence: Severity
        if request.severity:
            severity = request.severity
            sev_conf = 1.0
            sev_override = False
            sev_rationale = ["Explicit severity supplied by request"]
        else:
            severity, sev_conf, sev_override, sev_rationale = severity_engine.evaluate(
                normalized_text, entities
            )

        # 5. AI Intelligence: Routing
        recommendation = routing_service.recommend_assignment(
            category_name=category_name,
            severity=severity
        )

        # 6. SLA Calculation
        sla_due = sla_service.calculate_due_date(severity, from_time=now)

        # 7. Persist Complaint
        db.complaints[complaint_id] = {
            "id": complaint_id,
            "user_id": request.user_id or actor_id or list(db.users.keys())[0],
            "raw_text": request.complaint_text,
            "normalized_text": normalized_text,
            "language": "en",
            "created_at": now
        }

        # 8. Record AI Decisions
        ai_decisions_list: List[AIDecision] = []

        cat_decision = AIDecision(
            id=uuid4(),
            ticket_id=ticket_id,
            decision_type="category",
            value={"category_id": str(category_id), "category_name": category_name},
            confidence=cat_conf,
            model_name=category_classifier.model_name,
            model_version=category_classifier.model_version,
            policy_version=settings.POLICY_VERSION
        )
        db.ai_decisions[cat_decision.id] = cat_decision.model_dump()
        ai_decisions_list.append(cat_decision)

        sev_decision = AIDecision(
            id=uuid4(),
            ticket_id=ticket_id,
            decision_type="severity",
            value={"severity": severity, "override_applied": sev_override, "rationale": sev_rationale},
            confidence=sev_conf,
            model_name=severity_engine.model_name,
            model_version=severity_engine.model_version,
            policy_version=settings.POLICY_VERSION
        )
        db.ai_decisions[sev_decision.id] = sev_decision.model_dump()
        ai_decisions_list.append(sev_decision)

        route_decision = AIDecision(
            id=uuid4(),
            ticket_id=ticket_id,
            decision_type="routing",
            value=recommendation.model_dump(),
            confidence=recommendation.score,
            model_name="routing-scoring-engine",
            model_version=recommendation.model_version,
            policy_version=settings.POLICY_VERSION
        )
        db.ai_decisions[route_decision.id] = route_decision.model_dump()
        ai_decisions_list.append(route_decision)

        # 9. Persist Ticket (System of Record)
        ticket_record = {
            "id": ticket_id,
            "complaint_id": complaint_id,
            "complaint_text": request.complaint_text,
            "category_id": category_id,
            "severity": severity,
            "status": "OPEN",
            "team_id": recommendation.team_id,
            "assigned_agent_id": recommendation.agent_id,
            "sla_due_at": sla_due,
            "resolved_at": None,
            "version": 1,
            "created_at": now,
            "updated_at": now
        }
        db.tickets[ticket_id] = ticket_record

        # 10. Record Ticket Lifecycle Event
        db.ticket_events.append({
            "id": uuid4(),
            "ticket_id": ticket_id,
            "event_type": "TICKET_CREATED",
            "actor_type": "SYSTEM",
            "actor_id": actor_id,
            "payload": {
                "initial_severity": severity,
                "initial_team_id": str(recommendation.team_id),
                "initial_agent_id": str(recommendation.agent_id) if recommendation.agent_id else None,
                "source": request.source
            },
            "created_at": now
        })

        # 11. Transactional Outbox Event
        outbox_service.publish_event(
            aggregate_type="TICKET",
            aggregate_id=ticket_id,
            event_type="TICKET_CREATED_EVENT",
            payload={"ticket_id": str(ticket_id), "severity": severity, "sla_due_at": sla_due.isoformat()}
        )

        # 12. Audit Log
        audit_service.log_action(
            actor_id=actor_id,
            action="CREATE_TICKET",
            resource_type="TICKET",
            resource_id=ticket_id,
            before=None,
            after={"status": "OPEN", "severity": severity, "version": 1}
        )

        # 13. Cache for Idempotency
        if request.client_idempotency_key:
            db.idempotency_records[request.client_idempotency_key] = ticket_id

        return self._format_ticket_response(ticket_record, ai_decisions_list)

    def get_ticket_by_id(self, ticket_id: UUID) -> TicketResponse:
        if ticket_id not in db.tickets:
            raise EntityNotFoundException("Ticket", str(ticket_id))
        
        ticket = db.tickets[ticket_id]
        decisions = [
            AIDecision(**d) for d in db.ai_decisions.values()
            if d.get("ticket_id") == ticket_id
        ]
        return self._format_ticket_response(ticket, decisions)

    def assign_ticket(
        self,
        ticket_id: UUID,
        agent_id: UUID,
        version: int,
        actor_id: Optional[UUID] = None,
        rationale: Optional[str] = None
    ) -> TicketResponse:
        ticket = self._get_ticket_or_404(ticket_id)

        # Optimistic Concurrency Control (OCC)
        if ticket["version"] != version:
            raise ConflictException(
                f"Ticket version conflict. Expected version {version}, but database version is {ticket['version']}."
            )

        if agent_id not in db.agents:
            raise EntityNotFoundException("Agent", str(agent_id))

        before_state = dict(ticket)
        now = datetime.now(timezone.utc)
        agent = db.agents[agent_id]

        ticket["assigned_agent_id"] = agent_id
        ticket["team_id"] = agent["team_id"]
        ticket["status"] = "IN_PROGRESS"
        ticket["version"] += 1
        ticket["updated_at"] = now

        db.ticket_events.append({
            "id": uuid4(),
            "ticket_id": ticket_id,
            "event_type": "TICKET_ASSIGNED",
            "actor_type": "USER",
            "actor_id": actor_id,
            "payload": {"agent_id": str(agent_id), "rationale": rationale},
            "created_at": now
        })

        audit_service.log_action(
            actor_id=actor_id,
            action="ASSIGN_TICKET",
            resource_type="TICKET",
            resource_id=ticket_id,
            before={"status": before_state["status"], "assigned_agent_id": str(before_state["assigned_agent_id"])},
            after={"status": ticket["status"], "assigned_agent_id": str(agent_id), "version": ticket["version"]}
        )

        return self.get_ticket_by_id(ticket_id)

    def escalate_ticket(
        self,
        ticket_id: UUID,
        reason: str,
        target_tier: str,
        version: int,
        actor_id: Optional[UUID] = None
    ) -> TicketResponse:
        ticket = self._get_ticket_or_404(ticket_id)

        # OCC Check
        if ticket["version"] != version:
            raise ConflictException(f"Version mismatch: current is {ticket['version']}, provided is {version}.")

        before_state = dict(ticket)
        now = datetime.now(timezone.utc)

        # Escalate team to Tier-2
        tier2_team_id = None
        for tid, tm in db.teams.items():
            if "tier-2" in tm["name"].lower() or "escalation" in tm["name"].lower():
                tier2_team_id = tid
                break

        ticket["status"] = "ESCALATED"
        if tier2_team_id:
            ticket["team_id"] = tier2_team_id
        ticket["severity"] = "URGENT" if ticket["severity"] == "HIGH" else ticket["severity"]
        ticket["version"] += 1
        ticket["updated_at"] = now

        db.ticket_events.append({
            "id": uuid4(),
            "ticket_id": ticket_id,
            "event_type": "TICKET_ESCALATED",
            "actor_type": "USER",
            "actor_id": actor_id,
            "payload": {"reason": reason, "target_tier": target_tier},
            "created_at": now
        })

        outbox_service.publish_event(
            aggregate_type="TICKET",
            aggregate_id=ticket_id,
            event_type="TICKET_ESCALATED_EVENT",
            payload={"reason": reason, "target_tier": target_tier}
        )

        audit_service.log_action(
            actor_id=actor_id,
            action="ESCALATE_TICKET",
            resource_type="TICKET",
            resource_id=ticket_id,
            before={"status": before_state["status"], "severity": before_state["severity"]},
            after={"status": ticket["status"], "severity": ticket["severity"], "version": ticket["version"]}
        )

        return self.get_ticket_by_id(ticket_id)

    def resolve_ticket(
        self,
        ticket_id: UUID,
        resolution_notes: str,
        resolution_code: str,
        version: int,
        actor_id: Optional[UUID] = None
    ) -> TicketResponse:
        ticket = self._get_ticket_or_404(ticket_id)

        # OCC Check
        if ticket["version"] != version:
            raise ConflictException(f"Version mismatch: current is {ticket['version']}, provided is {version}.")

        before_state = dict(ticket)
        now = datetime.now(timezone.utc)

        ticket["status"] = "RESOLVED"
        ticket["resolved_at"] = now
        ticket["version"] += 1
        ticket["updated_at"] = now

        db.ticket_events.append({
            "id": uuid4(),
            "ticket_id": ticket_id,
            "event_type": "TICKET_RESOLVED",
            "actor_type": "USER",
            "actor_id": actor_id,
            "payload": {"resolution_notes": resolution_notes, "resolution_code": resolution_code},
            "created_at": now
        })

        audit_service.log_action(
            actor_id=actor_id,
            action="RESOLVE_TICKET",
            resource_type="TICKET",
            resource_id=ticket_id,
            before={"status": before_state["status"], "resolved_at": None},
            after={"status": "RESOLVED", "resolved_at": now.isoformat(), "version": ticket["version"]}
        )

        return self.get_ticket_by_id(ticket_id)

    def _get_ticket_or_404(self, ticket_id: UUID) -> Dict[str, Any]:
        if ticket_id not in db.tickets:
            raise EntityNotFoundException("Ticket", str(ticket_id))
        return db.tickets[ticket_id]

    def _format_ticket_response(
        self,
        ticket: Dict[str, Any],
        ai_decisions: List[AIDecision]
    ) -> TicketResponse:
        cat_name = db.categories[ticket["category_id"]]["name"] if ticket.get("category_id") in db.categories else None
        team_name = db.teams[ticket["team_id"]]["name"] if ticket.get("team_id") in db.teams else None
        agent_name = db.agents[ticket["assigned_agent_id"]].get("name") if ticket.get("assigned_agent_id") in db.agents else None

        sla_status, _ = sla_service.evaluate_status(
            ticket["sla_due_at"], ticket.get("resolved_at")
        ) if ticket.get("sla_due_at") else ("ON_TRACK", 0)

        return TicketResponse(
            id=ticket["id"],
            complaint_id=ticket["complaint_id"],
            complaint_text=ticket["complaint_text"],
            category_id=ticket.get("category_id"),
            category_name=cat_name,
            severity=ticket["severity"],
            status=ticket["status"],
            team_id=ticket.get("team_id"),
            team_name=team_name,
            assigned_agent_id=ticket.get("assigned_agent_id"),
            assigned_agent_name=agent_name,
            sla_due_at=ticket.get("sla_due_at"),
            sla_status=sla_status,
            resolved_at=ticket.get("resolved_at"),
            version=ticket["version"],
            created_at=ticket["created_at"],
            updated_at=ticket["updated_at"],
            ai_decisions=ai_decisions
        )

ticket_service = TicketService()
