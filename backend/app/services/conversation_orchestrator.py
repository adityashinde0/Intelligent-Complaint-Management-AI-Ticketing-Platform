from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID, uuid4
from app.core.config import settings
from app.core.database import db
from app.ml.classifiers.intent_classifier import intent_classifier
from app.services.rag_service import rag_service
from app.services.ticket_service import ticket_service
from app.schemas.api import ConversationMessage, MessageResponse, TicketCreate

class ConversationOrchestrator:
    """Orchestrates customer conversation turns, routing between
    grounded RAG resolution, structured clarification, and transactional ticket creation.
    """

    def process_message(
        self,
        message: ConversationMessage,
        user_id: Optional[UUID] = None
    ) -> MessageResponse:
        now = datetime.now(timezone.utc)
        conversation_id = message.conversation_id or uuid4()

        # Initialize conversation session if new
        if conversation_id not in db.conversations:
            db.conversations[conversation_id] = {
                "id": conversation_id,
                "user_id": user_id,
                "status": "ACTIVE",
                "created_at": now
            }

        # Save incoming customer message
        db.messages.append({
            "id": uuid4(),
            "conversation_id": conversation_id,
            "sender": "CUSTOMER",
            "text": message.text,
            "client_message_id": message.client_message_id,
            "created_at": now
        })

        normalized_text = intent_classifier.normalize_text(message.text)
        intent, intent_confidence = intent_classifier.classify_intent(normalized_text)
        entities = intent_classifier.extract_entities(normalized_text)

        # -------------------------------------------------------------
        # BRANCH 1: FAQ / Knowledge Query -> RAG Resolution
        # -------------------------------------------------------------
        if intent == "FAQ_QUERY":
            answer, rag_confidence, citations = rag_service.answer_query(normalized_text)
            if answer and rag_confidence >= settings.RAG_CONFIDENCE_THRESHOLD:
                # Store system response
                db.messages.append({
                    "id": uuid4(),
                    "conversation_id": conversation_id,
                    "sender": "ASSISTANT",
                    "text": answer,
                    "created_at": datetime.now(timezone.utc)
                })

                return MessageResponse(
                    status="success",
                    message_id=uuid4(),
                    conversation_id=conversation_id,
                    response=answer,
                    confidence=rag_confidence,
                    intent=intent,
                    suggested_actions=["Was this helpful?", "I still need assistance"],
                    citations=citations,
                    ticket_id=None
                )

        # -------------------------------------------------------------
        # BRANCH 2: Ambiguous / Incomplete Context -> Clarification Gate
        # -------------------------------------------------------------
        if len(normalized_text.split()) < 3 and not entities:
            clarification_msg = "Could you please specify your account ID, service location, or what error message appears on your device?"
            db.messages.append({
                "id": uuid4(),
                "conversation_id": conversation_id,
                "sender": "ASSISTANT",
                "text": clarification_msg,
                "created_at": datetime.now(timezone.utc)
            })

            return MessageResponse(
                status="clarifying",
                message_id=uuid4(),
                conversation_id=conversation_id,
                response=clarification_msg,
                confidence=0.85,
                intent="CLARIFYING",
                suggested_actions=["Provide Account ID", "Describe LED lights", "Report Outage"],
                citations=[],
                ticket_id=None
            )

        # -------------------------------------------------------------
        # BRANCH 3: Complaint Intake -> Transactional Ticket Creation
        # -------------------------------------------------------------
        ticket_req = TicketCreate(
            complaint_text=message.text,
            source="CHATBOT",
            extracted_entities=entities,
            user_id=user_id,
            client_idempotency_key=str(message.client_message_id)
        )
        ticket_res = ticket_service.create_ticket_transactional(ticket_req, actor_id=user_id)

        response_text = (
            f"I have registered your complaint under Ticket #{str(ticket_res.id)[:8]}. "
            f"Our {ticket_res.team_name} team has been assigned (Severity: {ticket_res.severity}). "
            f"Expected resolution within {settings.SLA_URGENT_HOURS if ticket_res.severity == 'URGENT' else settings.SLA_HIGH_HOURS if ticket_res.severity == 'HIGH' else settings.SLA_MEDIUM_HOURS} hours."
        )

        db.messages.append({
            "id": uuid4(),
            "conversation_id": conversation_id,
            "sender": "ASSISTANT",
            "text": response_text,
            "created_at": datetime.now(timezone.utc)
        })

        return MessageResponse(
            status="escalated_to_ticket",
            message_id=uuid4(),
            conversation_id=conversation_id,
            response=response_text,
            confidence=intent_confidence,
            intent=intent,
            suggested_actions=["Track Ticket Status", "Upload Photos/Attachments", "Speak with Agent"],
            citations=[],
            ticket_id=ticket_res.id
        )

conversation_orchestrator = ConversationOrchestrator()
