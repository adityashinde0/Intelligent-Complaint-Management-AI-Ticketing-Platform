from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import UUID
from fastapi import APIRouter, Depends
from app.core.auth import get_current_user, require_role
from app.core.database import db
from app.schemas.api import AgentQueueItem, UserResponse

router = APIRouter(prefix="/agents", tags=["Agents & Queues"])

@router.get("/queue", response_model=List[AgentQueueItem])
async def get_agent_queue(
    current_user: UserResponse = Depends(require_role(["agent", "admin"]))
):
    now = datetime.now(timezone.utc)
    queue: List[AgentQueueItem] = []

    for tid, t in db.tickets.items():
        if t["status"] in ["OPEN", "IN_PROGRESS", "ESCALATED"]:
            # If agent, prioritize tickets assigned to them or their team
            if current_user.role == "agent":
                if t.get("assigned_agent_id") != current_user.id:
                    continue

            cat_name = db.categories.get(t.get("category_id"), {}).get("name", "General")
            due_at = t["sla_due_at"]
            if due_at.tzinfo is None:
                due_at = due_at.replace(tzinfo=timezone.utc)
            remaining_mins = int((due_at - now).total_seconds() / 60)

            queue.append(AgentQueueItem(
                ticket_id=tid,
                severity=t["severity"],
                status=t["status"],
                category_name=cat_name,
                complaint_summary=t["complaint_text"][:120] + ("..." if len(t["complaint_text"]) > 120 else ""),
                sla_due_at=due_at,
                sla_remaining_minutes=remaining_mins,
                created_at=t["created_at"]
            ))

    # Sort queue by severity priority (URGENT first) and SLA remaining minutes
    severity_order = {"URGENT": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    queue.sort(key=lambda x: (severity_order.get(x.severity, 4), x.sla_remaining_minutes))
    return queue

@router.get("", response_model=List[Dict[str, Any]])
async def list_agents(
    current_user: UserResponse = Depends(require_role(["agent", "admin"]))
):
    agents_out = []
    for aid, a in db.agents.items():
        team_name = db.teams.get(a["team_id"], {}).get("name", "Unknown")
        agents_out.append({
            "id": aid,
            "name": a["name"],
            "team_id": a["team_id"],
            "team_name": team_name,
            "availability_status": a["availability_status"],
            "capacity": a["capacity"],
            "current_load": a["current_load"],
            "skills": a["skills"],
            "language_codes": a["language_codes"]
        })
    return agents_out
