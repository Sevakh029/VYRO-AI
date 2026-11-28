from datetime import UTC, datetime, timedelta

from vyro_backend.in_memory_state import InMemoryTrafficState
from vyro_backend.orchestrator import BackendOrchestrator
from vyro_backend.schemas import IntersectionState
from vyro_controller.safety import signal_safety_from_dict
from vyro_controller.state import Action


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


def safety_configs(*signal_ids: str) -> dict:
    result = {}
    for signal_id in signal_ids or ("signal-1", "signal-2"):
        result[signal_id] = signal_safety_from_dict(
            {
                "signal_id": signal_id,
                "phases": [
                    {
                        "phase": 0,
                        "kind": "green",
                        "minimum_green_s": 5,
                        "yellow_s": 0,
                        "all_red_s": 0,
                    },
                    {
                        "phase": 1,
                        "kind": "yellow",
                        "minimum_green_s": 4,
                        "yellow_s": 4,
                        "all_red_s": 0,
                    },
                    {
                        "phase": 2,
                        "kind": "all_red",
                        "minimum_green_s": 5,
                        "yellow_s": 0,
                        "all_red_s": 5,
                    },
                ],
                "yellow_phase": 1,
                "all_red_phase": 2,
                "max_wait_s": 120,
            }
        )
    return result


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
    orchestrator = BackendOrchestrator(
        state,
        publisher,
        signal_configs=safety_configs("signal-1"),
    )

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
        signal_configs=safety_configs("signal-1", "signal-2"),
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


def test_orchestrator_rejects_action_not_in_trusted_config(tmp_path) -> None:
    config = tmp_path / "signals.json"
    config.write_text(
        '{"signals":[{"signal_id":"signal-1","phases":[{"phase":0,"kind":"green","minimum_green_s":20,"yellow_s":0,"all_red_s":0},{"phase":1,"kind":"yellow","minimum_green_s":4,"yellow_s":4,"all_red_s":0},{"phase":2,"kind":"all_red","minimum_green_s":5,"yellow_s":0,"all_red_s":5}],"yellow_phase":1,"all_red_phase":2,"max_wait_s":120}]}',
        encoding="utf-8",
    )
    state = InMemoryTrafficState()
    add_intersection(state)
    publisher = FakePublisher()
    orchestrator = BackendOrchestrator(
        state,
        publisher,
        controller=lambda system_state: Action(
            intersection_id="signal-1",
            phase_id=99,
            reason="unsafe",
            timestamp=datetime.now(UTC),
        ),
        signal_config_path=str(config),
    )

    assert orchestrator.tick() == []
    assert publisher.commands == []


def test_orchestrator_controls_only_configured_signal(tmp_path) -> None:
    config = tmp_path / "signals.json"
    config.write_text(
        '{"signals":[{"signal_id":"signal-1","phases":[{"phase":0,"kind":"green","minimum_green_s":20,"yellow_s":0,"all_red_s":0},{"phase":1,"kind":"yellow","minimum_green_s":4,"yellow_s":4,"all_red_s":0},{"phase":2,"kind":"all_red","minimum_green_s":5,"yellow_s":0,"all_red_s":5}],"yellow_phase":1,"all_red_phase":2,"max_wait_s":120}]}',
        encoding="utf-8",
    )
    state = InMemoryTrafficState()
    timestamp = datetime.now(UTC)
    for signal_id in ("signal-1", "signal-2"):
        state.receive_intersection(
            IntersectionState(
                intersection_id=signal_id,
                phase_id=0,
                time_in_phase_s=30,
                timestamp=timestamp,
            )
        )
    publisher = FakePublisher()
    orchestrator = BackendOrchestrator(
        state,
        publisher,
        controller=lambda system_state: Action(
            intersection_id=system_state.intersection_id,
            phase_id=0,
            reason="hold",
            timestamp=timestamp,
        ),
        controlled_signal_ids=("signal-1",),
        signal_config_path=str(config),
    )

    commands = orchestrator.tick()
    assert [command.signal_id for command in commands] == ["signal-1"]
