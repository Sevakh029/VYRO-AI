import hashlib
import json
from pathlib import Path

PERSONAL_FIELD_NAMES = {
    "name",
    "email",
    "phone",
    "home_address",
    "license_plate",
    "gps_exact",
}


def pseudonymize_vehicle_id(vehicle_id: str, run_id: str) -> str:
    if not vehicle_id or not run_id:
        raise ValueError("vehicle_id and run_id must be non-empty")
    digest = hashlib.sha256(f"{run_id}:{vehicle_id}".encode()).hexdigest()
    return f"pseud-{digest[:16]}"


def schema_check_for_personal_fields(payload: bytes) -> list[str]:
    try:
        value = json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return []
    if not isinstance(value, dict):
        return []
    return sorted(
        key
        for key in value
        if key.lower().replace("-", "_") in PERSONAL_FIELD_NAMES
    )


def load_json_config(path: str | Path) -> dict[str, object]:
    config_path = Path(path)
    with config_path.open(encoding="utf-8") as file:
        value = json.load(file)
    if not isinstance(value, dict):
        raise ValueError("configuration must be a JSON object")
    return value
