from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import UUID, uuid4
from app.core.database import db

class OutboxService:
    """Transactional Outbox for durable, decoupled event delivery."""

    @staticmethod
    def publish_event(
        aggregate_type: str,
        aggregate_id: UUID,
        event_type: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        event = {
            "id": uuid4(),
            "aggregate_type": aggregate_type,
            "aggregate_id": aggregate_id,
            "event_type": event_type,
            "payload": payload,
            "status": "PENDING",
            "retry_count": 0,
            "created_at": datetime.now(timezone.utc)
        }
        db.outbox.append(event)
        return event

    @staticmethod
    def dispatch_pending_events() -> List[Dict[str, Any]]:
        """Processes and delivers pending outbox events."""
        dispatched = []
        for event in db.outbox:
            if event["status"] == "PENDING":
                # Mark as processed
                event["status"] = "PROCESSED"
                event["dispatched_at"] = datetime.now(timezone.utc)
                dispatched.append(event)
        return dispatched

outbox_service = OutboxService()
