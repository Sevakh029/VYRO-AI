from fastapi.testclient import TestClient
from vyro_backend.app import app


def test_health_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_state_and_scenario_endpoints() -> None:
    with TestClient(app) as client:
        initial = client.get("/state")
        started = client.post(
            "/scenario",
            json={"name": "heavy", "action": "start"},
        )
        stopped = client.post(
            "/scenario",
            json={"name": "heavy", "action": "stop"},
        )

    assert initial.status_code == 200
    assert started.status_code == 200
    assert started.json() == {"name": "heavy", "status": "running"}
    assert stopped.status_code == 200
    assert stopped.json() == {"name": "heavy", "status": "stopped"}
