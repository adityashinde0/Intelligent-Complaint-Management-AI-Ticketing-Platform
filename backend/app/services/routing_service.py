from typing import Any, Dict, List, Optional
from uuid import UUID
from app.core.config import settings
from app.core.database import db
from app.schemas.api import AssignmentRecommendation

class RoutingService:
    """Intelligent Routing & Assignment Engine implementing hard constraint
    filtering and multi-factor objective scoring.
    """

    def __init__(self):
        self.model_version = settings.ROUTING_MODEL_VERSION

    def recommend_assignment(
        self,
        category_name: str,
        severity: str,
        language: str = "en"
    ) -> AssignmentRecommendation:
        rationale: List[str] = []
        eligible_candidates: List[Dict[str, Any]] = []

        # 1. Determine Target Team
        team_id = None
        team_name = "Support Operations"
        
        if "network" in category_name.lower() or "outage" in category_name.lower():
            for tid, tm in db.teams.items():
                if "network" in tm["name"].lower():
                    team_id = tid
                    team_name = tm["name"]
                    break
        elif "billing" in category_name.lower():
            for tid, tm in db.teams.items():
                if "billing" in tm["name"].lower():
                    team_id = tid
                    team_name = tm["name"]
                    break

        if not team_id:
            # Default to first team or overflow
            team_id = list(db.teams.keys())[0]
            team_name = db.teams[team_id]["name"]

        # 2. Hard Constraint Evaluation: H(a, t) in {0, 1}
        for agent_id, agent in db.agents.items():
            # Check availability
            if agent["availability_status"] != "AVAILABLE":
                continue
            # Check capacity margin
            if agent["current_load"] >= agent["capacity"]:
                continue
            # Check team alignment
            if agent["team_id"] != team_id:
                continue
            # Check language match
            agent_langs = [l.strip().lower() for l in agent["language_codes"].split(",")]
            if language.lower() not in agent_langs:
                continue

            eligible_candidates.append(agent)

        # 3. Handle Fallback if no agents meet hard constraints (Failure Matrix Fallback)
        if not eligible_candidates:
            # Route to Overflow Team
            overflow_team_id = None
            for tid, tm in db.teams.items():
                if "overflow" in tm["name"].lower():
                    overflow_team_id = tid
                    break
            
            rationale.append("Hard constraints satisfied: 0 active agents available in primary team")
            rationale.append("Routing to Overflow queue for automated escalation")
            return AssignmentRecommendation(
                team_id=overflow_team_id or team_id,
                team_name="Overflow Queue",
                agent_id=None,
                agent_name=None,
                score=0.0,
                hard_constraints_satisfied=False,
                rationale=rationale,
                model_version=self.model_version
            )

        # 4. Multi-Factor Scoring: Score(a, t) = sum(w_j * f_j)
        best_agent = None
        highest_score = -1.0
        best_rationale: List[str] = []

        for agent in eligible_candidates:
            # Factor 1: Available capacity ratio (weight = 0.40)
            capacity_ratio = (agent["capacity"] - agent["current_load"]) / agent["capacity"]
            
            # Factor 2: Skill match (weight = 0.40)
            skills = agent.get("skills", [])
            matched_skills = [s for s in skills if s in category_name.lower()]
            skill_score = 1.0 if matched_skills else 0.5
            
            # Factor 3: Base reliability factor (weight = 0.20)
            reliability_score = 0.95

            final_score = (0.40 * capacity_ratio) + (0.40 * skill_score) + (0.20 * reliability_score)
            
            if final_score > highest_score:
                highest_score = final_score
                best_agent = agent
                best_rationale = [
                    f"Passed all hard constraints (status=AVAILABLE, load={agent['current_load']}/{agent['capacity']})",
                    f"High capacity margin: {round(capacity_ratio * 100, 1)}% available",
                    f"Skill alignment score: {round(skill_score, 2)}",
                    f"Selected as optimal operator with composite score {round(final_score, 4)}"
                ]

        return AssignmentRecommendation(
            team_id=team_id,
            team_name=team_name,
            agent_id=best_agent["id"],
            agent_name=best_agent.get("name", "Assigned Agent"),
            score=round(highest_score, 4),
            hard_constraints_satisfied=True,
            rationale=best_rationale,
            model_version=self.model_version
        )

routing_service = RoutingService()
