from fastapi.testclient import TestClient
from app.main import app
import uuid

client = TestClient(app)

def test_send_message():
    response = client.post("/v1/conversations/messages", json={
        "client_message_id": str(uuid.uuid4()),
        "text": "My internet is down"
    })
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_create_ticket():
    response = client.post("/v1/tickets", json={
        "complaint_text": "My internet is down",
        "category_id": str(uuid.uuid4()),
        "severity": "HIGH",
        "source": "WEB",
        "extracted_entities": {}
    })
    assert response.status_code == 200
    assert response.json()["status"] == "created"

if __name__ == "__main__":
    test_send_message()
    test_create_ticket()
    print("All tests passed successfully.")
