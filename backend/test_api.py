import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import db
from app.ml.evaluation.harness import evaluation_harness

client = TestClient(app)

def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "policy_version" in data

def test_auth_and_rbac():
    # 1. Login as customer
    res = client.post("/v1/auth/login", json={"email": "customer@enterprise.com", "password": "password123"})
    assert res.status_code == 200
    cust_token = res.json()["access_token"]
    
    # 2. Login as agent
    res = client.post("/v1/auth/login", json={"email": "sarah.agent@enterprise.com", "password": "password123"})
    assert res.status_code == 200
    agent_token = res.json()["access_token"]

    # 3. Login as admin
    res = client.post("/v1/auth/login", json={"email": "admin@enterprise.com", "password": "password123"})
    assert res.status_code == 200
    admin_token = res.json()["access_token"]

    # 4. Check profile with customer token
    res = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {cust_token}"})
    assert res.status_code == 200
    assert res.json()["role"] == "customer"

    # 5. Customer accessing admin endpoint -> 403 Forbidden
    res = client.get("/v1/admin/models", headers={"Authorization": f"Bearer {cust_token}"})
    assert res.status_code == 403

    # 6. Admin accessing admin endpoint -> 200 OK
    res = client.get("/v1/admin/models", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    assert len(res.json()) > 0

def test_faq_resolution_via_rag():
    # Customer asks about router reset procedure
    res = client.post("/v1/conversations/messages", json={
        "client_message_id": str(uuid.uuid4()),
        "text": "How do I power-cycle my router? Looking for instructions."
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["confidence"] >= 0.85
    assert len(data["citations"]) > 0
    assert "power-cycle" in data["response"].lower() or "router" in data["response"].lower()

def test_clarification_gate():
    # Ambiguous, under-specified input
    res = client.post("/v1/conversations/messages", json={
        "client_message_id": str(uuid.uuid4()),
        "text": "Broken."
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "clarifying"
    assert len(data["suggested_actions"]) > 0

def test_ticket_creation_and_ai_decisions():
    # Actual complaint creates ticket atomically
    msg_id = str(uuid.uuid4())
    res = client.post("/v1/conversations/messages", json={
        "client_message_id": msg_id,
        "text": "Fiber broadband connection is completely severed in our warehouse Acct #98421."
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "escalated_to_ticket"
    assert data["ticket_id"] is not None
    
    ticket_id = data["ticket_id"]
    # Verify ticket in database
    t_res = client.get(f"/v1/tickets/{ticket_id}")
    assert t_res.status_code == 200
    ticket_data = t_res.json()
    assert ticket_data["status"] == "OPEN"
    assert ticket_data["severity"] in ["HIGH", "URGENT"]
    assert len(ticket_data["ai_decisions"]) >= 3
    assert ticket_data["sla_due_at"] is not None

def test_idempotency_protection():
    idempotency_key = f"key-{uuid.uuid4()}"
    payload = {
        "complaint_text": "Duplicate submission test for payment glitch",
        "source": "WEB",
        "client_idempotency_key": idempotency_key
    }

    # First call
    res1 = client.post("/v1/tickets", json=payload)
    assert res1.status_code == 201
    tid1 = res1.json()["id"]

    # Second call with same idempotency key
    res2 = client.post("/v1/tickets", json=payload)
    assert res2.status_code == 200 or res2.status_code == 201
    tid2 = res2.json()["id"]

    assert tid1 == tid2, "Idempotent requests must return the exact same ticket entity"

def test_severity_deterministic_override():
    # Emergency hospital trigger must be forced to URGENT
    res = client.post("/v1/tickets", json={
        "complaint_text": "Emergency: hospital telemetry link down due to security breach and ransomware!",
        "source": "API"
    })
    assert res.status_code == 201
    data = res.json()
    assert data["severity"] == "URGENT"
    # Find severity decision
    sev_decision = next(d for d in data["ai_decisions"] if d["decision_type"] == "severity")
    assert sev_decision["value"]["override_applied"] is True

def test_optimistic_concurrency_control_and_transitions():
    # 1. Create initial ticket
    res = client.post("/v1/tickets", json={
        "complaint_text": "Optical WAN blinking red after power surge",
        "source": "WEB"
    })
    assert res.status_code == 201
    ticket = res.json()
    ticket_id = ticket["id"]
    initial_version = ticket["version"]
    assert initial_version == 1

    # 2. Get Agent token
    login_res = client.post("/v1/auth/login", json={"email": "sarah.agent@enterprise.com", "password": "password123"})
    agent_token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {agent_token}"}

    # 3. Assign ticket with correct version
    agent_id = list(db.agents.keys())[0]
    assign_res = client.post(
        f"/v1/tickets/{ticket_id}/assign",
        headers=headers,
        json={"agent_id": str(agent_id), "version": initial_version, "rationale": "Specialist assigned"}
    )
    assert assign_res.status_code == 200
    updated_ticket = assign_res.json()
    assert updated_ticket["status"] == "IN_PROGRESS"
    assert updated_ticket["version"] == 2

    # 4. Attempt update with stale version -> Expect 409 Conflict
    stale_res = client.post(
        f"/v1/tickets/{ticket_id}/escalate",
        headers=headers,
        json={"reason": "Stale update attempt", "version": 1}
    )
    assert stale_res.status_code == 409
    assert "Conflict" in stale_res.json()["title"]

    # 5. Escalate with valid version
    esc_res = client.post(
        f"/v1/tickets/{ticket_id}/escalate",
        headers=headers,
        json={"reason": "Fiber splice needed", "version": 2}
    )
    assert esc_res.status_code == 200
    esc_ticket = esc_res.json()
    assert esc_ticket["status"] == "ESCALATED"
    assert esc_ticket["version"] == 3

    # 6. Resolve with valid version
    res_res = client.post(
        f"/v1/tickets/{ticket_id}/resolve",
        headers=headers,
        json={"resolution_notes": "Spliced fiber and verified optical signal", "version": 3}
    )
    assert res_res.status_code == 200
    assert res_res.json()["status"] == "RESOLVED"
    assert res_res.json()["version"] == 4

    # 7. Check timeline events
    events_res = client.get(f"/v1/tickets/{ticket_id}/events")
    assert events_res.status_code == 200
    event_types = [e["event_type"] for e in events_res.json()]
    assert "TICKET_CREATED" in event_types
    assert "TICKET_ASSIGNED" in event_types
    assert "TICKET_ESCALATED" in event_types
    assert "TICKET_RESOLVED" in event_types

def test_agent_queue_and_analytics():
    # Agent token
    login_res = client.post("/v1/auth/login", json={"email": "sarah.agent@enterprise.com", "password": "password123"})
    agent_token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {agent_token}"}

    # Queue
    q_res = client.get("/v1/agents/queue", headers=headers)
    assert q_res.status_code == 200
    assert isinstance(q_res.json(), list)

    # Analytics
    an_res = client.get("/v1/analytics/overview")
    assert an_res.status_code == 200
    metrics = an_res.json()
    assert "open_tickets" in metrics
    assert "sla_breach_rate" in metrics
    assert "ai_automation_rate" in metrics

def test_ai_evaluation_benchmark_targets():
    results = evaluation_harness.run_evaluation()
    assert results["targets_satisfied"] is True
    assert results["category_macro_f1"] >= 0.90
    assert results["severity_macro_f1"] >= 0.88
    assert results["urgent_recall"] >= 0.95
    assert results["retrieval_recall_at_5"] >= 0.95
    assert results["groundedness"] >= 0.98
    assert results["unsupported_answer_rate"] <= 0.01

if __name__ == "__main__":
    pytest.main(["-v", "test_api.py"])
