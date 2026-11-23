import json

from vyro_backend.agent_config import AgentConfig


def test_agent_config_loads_and_creates_runner(tmp_path) -> None:
    path = tmp_path / "agent.json"
    path.write_text(
        json.dumps(
            {
                "penetration": 0.6,
                "radius_m": 250,
                "seed": 100,
                "delay_seconds": 0.2,
                "jitter_seconds": 0.1,
                "drop_probability": 0.05,
            }
        ),
        encoding="utf-8",
    )

    config = AgentConfig.from_json(path)

    assert config.penetration == 0.6
    assert config.create_runner().penetration == 0.6
    assert config.create_publish_path().drop_probability == 0.05


def test_agent_config_rejects_unknown_fields(tmp_path) -> None:
    path = tmp_path / "agent.json"
    path.write_text(json.dumps({"penetration": 0.3, "unknown": True}), encoding="utf-8")

    try:
        AgentConfig.from_json(path)
    except ValueError:
        pass
    else:
        raise AssertionError("unknown agent config field was accepted")
