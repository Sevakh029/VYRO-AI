import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_compose_declares_mosquitto_and_backend() -> None:
    compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")

    assert "mosquitto:" in compose
    assert "backend:" in compose
    assert "condition: service_healthy" in compose
    assert "MQTT_HOST: mosquitto" in compose
    assert "127.0.0.1:8000:8000" in compose
    assert "127.0.0.1:1883:1883" in compose


def test_compose_mosquitto_healthcheck_requires_auth() -> None:
    compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")

    assert "mosquitto_pub" in compose
    assert "-u" in compose
    assert "-P" in compose
    assert "$MQTT_USERNAME" in compose
    assert "$MQTT_PASSWORD" in compose
    assert "MQTT_USERNAME" in compose
    assert "MQTT_PASSWORD" in compose


def test_docker_compose_config_when_docker_is_available() -> None:
    docker = shutil.which("docker")
    if docker is None:
        return

    env_file = ROOT / ".env"
    if not env_file.exists():
        env_file.write_text(
            "MQTT_USERNAME=vyro_test\n"
            "MQTT_PASSWORD=vyro-test-password\n"
            "VYRO_SQLITE_DB_PATH=data/vyro_messages.db\n",
            encoding="utf-8",
        )

    result = subprocess.run(
        [docker, "compose", "-f", str(ROOT / "compose.yaml"), "config", "--quiet"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stderr
