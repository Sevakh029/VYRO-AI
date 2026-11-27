from fastapi.testclient import TestClient
from vyro_backend.app import app


def test_health_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["mqtt_connected"] in ("true", "false")


def test_dashboard_origin_is_allowed_by_cors() -> None:
    with TestClient(app) as client:
        response = client.options(
            "/state",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


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
    assert started.json() == {"name": "heavy", "status": "running", "policy": "fixed"}
    assert stopped.status_code == 200
    assert stopped.json() == {"name": "heavy", "status": "stopped", "policy": "fixed"}


def test_scenario_supports_vyro_policy_and_invalid_policy() -> None:
    with TestClient(app) as client:
        started = client.post(
            "/scenario",
            json={"name": "normal", "action": "start", "policy": "vyro"},
        )
        stopped = client.post(
            "/scenario",
            json={"name": "normal", "action": "stop", "policy": "vyro"},
        )
        invalid = client.post(
            "/scenario",
            json={"name": "normal", "action": "start", "policy": "unknown"},
        )

    assert started.status_code == 200
    assert started.json()["policy"] == "vyro"
    assert started.json()["status"] == "running"
    assert stopped.status_code == 200
    assert stopped.json()["status"] == "stopped"
    assert invalid.status_code == 422


def test_state_endpoint_returns_empty_state_before_messages() -> None:
    with TestClient(app) as client:
        response = client.get("/state")

    assert response.status_code == 200
    assert "vehicles" in response.json()
    assert "intersections" in response.json()
    assert "commands" in response.json()
