from fastapi.testclient import TestClient
from main import app
from database import get_db, SessionLocal

client = TestClient(app)

def test_save_and_retrieve_workspace_config():
    # 1. Save Config
    payload = {
        "config": '{"layout_mode": "grid", "open_conversations": [1, 2, 3]}'
    }
    response = client.post("/admin/workspace", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # 2. Retrieve Config (via GET /admin/config)
    response = client.get("/admin/config")
    assert response.status_code == 200
    data = response.json()
    assert "workspace_config" in data
    assert data["workspace_config"] == payload["config"]
