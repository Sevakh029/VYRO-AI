from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
COMPOSE_CONFIG = PROJECT_ROOT / "compose.yaml"
MOSQUITTO_CONFIG = PROJECT_ROOT / "mosquitto" / "config" / "mosquitto.conf"
ENTRYPOINT = PROJECT_ROOT / "mosquitto" / "entrypoint.sh"


def test_compose_starts_authenticated_mosquitto_before_backend() -> None:
    compose = COMPOSE_CONFIG.read_text(encoding="utf-8")

    assert "mosquitto:" in compose
    assert "backend:" in compose
    assert 'MQTT_USERNAME: ${MQTT_USERNAME:?Set MQTT_USERNAME in .env}' in compose
    assert 'MQTT_PASSWORD: ${MQTT_PASSWORD:?Set MQTT_PASSWORD in .env}' in compose
    assert "condition: service_healthy" in compose
    assert "127.0.0.1:1883:1883" in compose
    assert "127.0.0.1:8000:8000" in compose


def test_compose_checks_broker_and_backend_health() -> None:
    compose = COMPOSE_CONFIG.read_text(encoding="utf-8")

    assert "mosquitto_pub" in compose
    assert "http://127.0.0.1:8000/health" in compose
    assert "ws://127.0.0.1:8000/ws" in compose


def test_mosquitto_requires_credentials_and_creates_password_file() -> None:
    broker_config = MOSQUITTO_CONFIG.read_text(encoding="utf-8")
    entrypoint = ENTRYPOINT.read_text(encoding="utf-8")

    assert "allow_anonymous false" in broker_config
    assert "password_file /mosquitto/data/passwords" in broker_config
    assert "mosquitto_passwd -c" in entrypoint
