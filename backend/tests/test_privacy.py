from vyro_backend.privacy import (
    pseudonymize_vehicle_id,
    schema_check_for_personal_fields,
)


def test_vehicle_pseudonym_is_run_specific_and_stable() -> None:
    first = pseudonymize_vehicle_id("vehicle-123", "run-a")
    second = pseudonymize_vehicle_id("vehicle-123", "run-a")

    assert first == second
    assert first.startswith("pseud-")
    assert first != "vehicle-123"
    assert pseudonymize_vehicle_id("vehicle-123", "run-b") != first


def test_schema_check_flags_personal_fields_without_mutating_payload() -> None:
    payload = b'{"email":"private@example.com","latitude":40.18}'

    assert schema_check_for_personal_fields(payload) == ["email"]
