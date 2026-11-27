from datetime import UTC, datetime, timedelta

from vyro_backend.in_memory_state import InMemoryTrafficState
from vyro_backend.orchestrator import BackendOrchestrator
from vyro_backend.schemas import IntersectionState
from vyro_controller.state import Action
from vyro_controller.types import Action as ControllerAction


class FakePublisher:
    def __init__(self) -> None:
        self.commands = []

    def publish(self, signal_id, phase, hold_s, reason):
        command = type("PublishedCommand", (), {
            "signal_id": signal_id,
            "phase": phase,
            "hold_s": hold_s,
            "reason": reason,
        })()
        self.commands.append(command)
        return command


def add_intersection(state, timestamp=None):
    state.receive_intersection(
        IntersectionState(
            intersection_id="signal-1",
            phase_id=1,
            time_in_phase_s=12,
            timestamp=timestamp or datetime.now(UTC),
        )
    )


def test_successful_tick_publishes_stub_action() -> None:
    state = InMemoryTrafficState()
    add_intersection(state)
    publisher = FakePublisher()
    orchestrator = BackendOrchestrator(state, publisher)

    commands = orchestrator.tick_once()

    assert len(commands) == 1
    assert publisher.commands[0].signal_id == "signal-1"
    assert publisher.commands[0].phase == 1


def test_missing_and_stale_state_are_skipped() -> None:
    state = InMemoryTrafficState()
    publisher = FakePublisher()
    orchestrator = BackendOrchestrator(state, publisher)
    assert orchestrator.tick() == []

    add_intersection(state, datetime.now(UTC) - timedelta(seconds=20))
    assert orchestrator.tick() == []
    assert publisher.commands == []


def test_empty_action_list_is_handled() -> None:
    state = InMemoryTrafficState()
    add_intersection(state)
    orchestrator = BackendOrchestrator(
        state,
        FakePublisher(),
        controller=lambda system_state: [],
    )

    assert orchestrator.tick() == []


def test_multiple_signal_actions_are_published() -> None:
    state = InMemoryTrafficState()
    timestamp = datetime.now(UTC)
    for signal_id in ("signal-1", "signal-2"):
        state.receive_intersection(
            IntersectionState(
                intersection_id=signal_id,
                phase_id=1,
                time_in_phase_s=10,
                timestamp=timestamp,
            )
        )
    publisher = FakePublisher()
    orchestrator = BackendOrchestrator(
        state,
        publisher,
        controller=lambda system_state: [
            Action(
                intersection_id=system_state.intersection_id,
                phase_id=2,
                reason="pressure",
                timestamp=timestamp,
            )
        ],
    )

    commands = orchestrator.tick()

    assert len(commands) == 2
    assert {command.signal_id for command in commands} == {"signal-1", "signal-2"}


def test_controller_action_is_published_with_its_hold_duration() -> None:
    state = InMemoryTrafficState()
    add_intersection(state)
    publisher = FakePublisher()
    orchestrator = BackendOrchestrator(
        state,
        publisher,
        controller=lambda system_state: [
            ControllerAction(
                signal_id=system_state.intersection_id,
                phase=2,
                hold_s=12.0,
                reason="pressure",
            )
        ],
    )

    commands = orchestrator.tick()

    assert len(commands) == 1
    assert publisher.commands[0].signal_id == "signal-1"
    assert publisher.commands[0].phase == 2
    assert publisher.commands[0].hold_s == 12.0


def test_controller_exception_is_logged_and_tick_continues() -> None:
    state = InMemoryTrafficState()
    add_intersection(state)
    publisher = FakePublisher()

    def broken_controller(system_state):
        raise RuntimeError("controller unavailable")

    orchestrator = BackendOrchestrator(state, publisher, controller=broken_controller)
    assert orchestrator.tick() == []
    assert publisher.commands == []


def test_command_publication_failure_does_not_raise() -> None:
    state = InMemoryTrafficState()
    add_intersection(state)

    class BrokenPublisher:
        def publish(self, *args):
            raise OSError("broker unavailable")

    orchestrator = BackendOrchestrator(state, BrokenPublisher())
    assert orchestrator.tick() == []
