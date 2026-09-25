from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID, uuid4
from app.core.database import db

class AuditService:
    """Records immutable audit logs capturing every state mutation and actor action."""

    @staticmethod
    def log_action(
        actor_id: Optional[UUID],
        action: str,
        resource_type: str,
        resource_id: UUID,
        before: Optional[Dict[str, Any]] = None,
        after: Optional[Dict[str, Any]] = None,
        request_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        entry = {
            "id": uuid4(),
            "actor_id": actor_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "before": before,
            "after": after,
            "request_id": request_id or uuid4(),
            "created_at": datetime.now(timezone.utc)
        }
        db.audit_logs.append(entry)
        return entry

audit_service = AuditService()
