from datetime import datetime, timedelta, timezone
from typing import Tuple
from app.core.config import settings

class SLAService:
    """Manages SLA target timelines, countdown clocks, and breach tracking."""

    @staticmethod
    def calculate_due_date(severity: str, from_time: datetime = None) -> datetime:
        base_time = from_time or datetime.now(timezone.utc)
        if base_time.tzinfo is None:
            base_time = base_time.replace(tzinfo=timezone.utc)
            
        hours = {
            "URGENT": settings.SLA_URGENT_HOURS,
            "HIGH": settings.SLA_HIGH_HOURS,
            "MEDIUM": settings.SLA_MEDIUM_HOURS,
            "LOW": settings.SLA_LOW_HOURS
        }.get(severity.upper(), settings.SLA_MEDIUM_HOURS)

        return base_time + timedelta(hours=hours)

    @staticmethod
    def evaluate_status(due_date: datetime, resolved_at: datetime = None) -> Tuple[str, int]:
        """Returns SLA status (ON_TRACK, AT_RISK, BREACHED) and remaining minutes."""
        now = datetime.now(timezone.utc)
        target_check = resolved_at or now
        if target_check.tzinfo is None:
            target_check = target_check.replace(tzinfo=timezone.utc)
        if due_date.tzinfo is None:
            due_date = due_date.replace(tzinfo=timezone.utc)

        diff = due_date - target_check
        remaining_minutes = int(diff.total_seconds() / 60)

        if remaining_minutes < 0:
            return "BREACHED", remaining_minutes
        elif remaining_minutes < 60:
            return "AT_RISK", remaining_minutes
        else:
            return "ON_TRACK", remaining_minutes

sla_service = SLAService()
