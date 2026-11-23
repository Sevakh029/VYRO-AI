import json
from pathlib import Path

import pytest
from pydantic import ValidationError
from vyro_backend.schemas import (
    IntersectionState,
    MetricsSnapshot,
    SignalCommand,
    VehicleAdvisory,
    VehicleState,
)

UTC_TIMESTAMP = "2026-11-20T10:00:00Z"


@pytest.mark.parametrize(
    ("model", "payload"),
    [
        (
            VehicleState,
            {
                "vehicle_id": "vehicle-1",
                "latitude": 40.18,
                "longitude": 44.51,
                "speed_mps": 12.5,
                "heading_deg": 90,
                "timestamp": UTC_TIMESTAMP,
            },
        ),
        (
            IntersectionState,
            {
                "intersection_id": "intersection-1",
                "phase_id": 2,
                "time_in_phase_s": 15.5,
                "detector_counts": {"approach_north": 4},
                "timestamp": UTC_TIMESTAMP,
            },
        ),
        (
            SignalCommand,
            {
                "intersection_id": "intersection-1",
                "phase_id": 1,
                "reason": "queue_pressure",
                "timestamp": UTC_TIMESTAMP,
            },
        ),
        (
            VehicleAdvisory,
            {
                "vehicle_id": "vehicle-1",
                "advisory_type": "speed",
                "message": "Reduce speed",
                "timestamp": UTC_TIMESTAMP,
            },
        ),
        (
            MetricsSnapshot,
            {
                "vehicle_count": 200,
                "mean_speed_mps": 8.2,
                "stopped_vehicle_count": 12,
                "timestamp": UTC_TIMESTAMP,
            },
        ),
    ],
)
def test_valid_schema_instances(model: type, payload: dict) -> None:
    instance = model.model_validate(payload)
    assert instance.timestamp.tzinfo is not None


@pytest.mark.parametrize(
    ("model", "payload"),
    [
        (
            VehicleState,
            {
                "vehicle_id": "vehicle-1",
                "latitude": 91,
                "longitude": 44.51,
                "speed_mps": 1,
                "timestamp": UTC_TIMESTAMP,
            },
        ),
        (
            IntersectionState,
            {
                "intersection_id": "intersection-1",
                "phase_id": -1,
                "time_in_phase_s": 1,
                "timestamp": UTC_TIMESTAMP,
            },
        ),
        (
            SignalCommand,
            {
                "intersection_id": "intersection-1",
                "phase_id": 1,
                "reason": "",
                "timestamp": UTC_TIMESTAMP,
            },
        ),
        (
            VehicleAdvisory,
            {
                "vehicle_id": "",
                "advisory_type": "speed",
                "message": "Reduce speed",
                "timestamp": UTC_TIMESTAMP,
            },
        ),
        (
            MetricsSnapshot,
            {
                "vehicle_count": -1,
                "mean_speed_mps": 5,
                "stopped_vehicle_count": 1,
                "timestamp": UTC_TIMESTAMP,
            },
        ),
    ],
)
def test_invalid_schema_values(model: type, payload: dict) -> None:
    with pytest.raises(ValidationError):
        model.model_validate(payload)


@pytest.mark.parametrize(
    "model",
    [VehicleState, IntersectionState, SignalCommand, VehicleAdvisory, MetricsSnapshot],
)
def test_missing_required_field_is_rejected(model: type) -> None:
    with pytest.raises(ValidationError):
        model.model_validate({})


@pytest.mark.parametrize(
    ("model", "example_name"),
    [
        (VehicleState, "vehicle_state.json"),
        (IntersectionState, "intersection_state.json"),
        (SignalCommand, "signal_command.json"),
        (VehicleAdvisory, "vehicle_advisory.json"),
        (MetricsSnapshot, "metrics_snapshot.json"),
    ],
)
def test_example_json_loads(model: type, example_name: str) -> None:
    example_path = (
        Path(__file__).parents[2] / "schemas" / "examples" / example_name
    )
    with example_path.open(encoding="utf-8") as file:
        payload = json.load(file)

    assert isinstance(model.model_validate(payload), model)


def test_schema_version_defaults_to_v1_0_and_accepts_explicit_value() -> None:
    payload = {
        "vehicle_id": "vehicle-1",
        "latitude": 40.18,
        "longitude": 44.51,
        "speed_mps": 12.5,
        "timestamp": UTC_TIMESTAMP,
    }

    defaulted = VehicleState.model_validate(payload)
    explicit = VehicleState.model_validate({**payload, "schema_version": "v1.0"})

    assert defaulted.schema_version == "v1.0"
    assert explicit.schema_version == "v1.0"
