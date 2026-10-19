import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from backend.app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["models_loaded"] is True
    assert data["data_ready"] is True

def test_twins_list():
    response = client.get("/api/twins")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    # ensure DT-01 exists
    ids = [d["twin_id"] for d in data]
    assert "DT-01" in ids

def test_twin_snapshot():
    response = client.get("/api/twins/DT-01")
    assert response.status_code == 200
    data = response.json()
    assert data["twin_id"] == "DT-01"
    assert "static" in data
    assert "dynamic" in data

def test_what_if():
    # first fetch snapshot to ensure twin is initialized
    client.get("/api/twins/DT-01")
    
    response = client.post(
        "/api/twins/DT-01/what-if",
        json={"carbs_g": 60.0, "activity_level": "moderate"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["scenarios"]) >= 2  # Baseline + 60g

def test_invalid_what_if():
    response = client.post(
        "/api/twins/DT-01/what-if",
        json={"carbs_g": 200.0, "activity_level": "moderate"}  # Over limit
    )
    assert response.status_code == 422 # Pydantic validation error

def test_replay_start_status_stop():
    response = client.post("/api/twins/DT-01/replay/start", json={"speed": 10.0})
    assert response.status_code == 200
    assert response.json()["status"] in ["started", "already_running"]
    
    response = client.get("/api/twins/DT-01/replay/status")
    assert response.status_code == 200
    # In TestClient, background tasks might not persist, so running may be False or True
    assert "running" in response.json()
    
    response = client.post("/api/twins/DT-01/replay/stop")
    assert response.status_code == 200
    
    response = client.get("/api/twins/DT-01/replay/status")
    assert response.status_code == 200
    assert response.json()["running"] is False

def test_websocket():
    with client.websocket_connect("/api/twins/DT-01/ws") as websocket:
        data = websocket.receive_json()
        assert data["event"] == "snapshot"
        assert data["twin_id"] == "DT-01"
