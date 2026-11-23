from vyro_backend.preemption import PreemptionCoordinator


def test_preemption_transitions_requested_granted_cleared() -> None:
    coordinator = PreemptionCoordinator()

    requested = coordinator.request("intersection-1", "ambulance-1", 8.0)
    granted = coordinator.grant("ambulance-1")
    cleared = coordinator.clear("ambulance-1")

    assert requested.state == "requested"
    assert granted.state == "granted"
    assert cleared.state == "cleared"
