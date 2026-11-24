from dataclasses import dataclass

import pytest

from sim.net_reader import phases_from_sumolib_program


@dataclass
class FakePhase:
    state: str
    duration: float


class FakeProgram:
    def __init__(self, phases: list[FakePhase]) -> None:
        self._phases = phases

    def getPhases(self) -> list[FakePhase]:
        return self._phases


def test_phase_reader_keeps_clearance_and_returns_plain_dataclasses() -> None:
    program = FakeProgram(
        [
            FakePhase("GG", 10),
            FakePhase("yy", 3),
            FakePhase("rr", 2),
            FakePhase("GG", 12),
        ]
    )

    result = phases_from_sumolib_program(program)

    assert [(phase.phase_id, phase.clearance_s) for phase in result] == [(0, 5), (3, 0)]


def test_phase_reader_ignores_green_yellow_transition_phases() -> None:
    program = FakeProgram([FakePhase("Gy", 4), FakePhase("rr", 2)])

    assert phases_from_sumolib_program(program) == ()


def test_phase_reader_rejects_invalid_clearance_duration() -> None:
    program = FakeProgram(
        [
            FakePhase("G", 10),
            FakePhase("yy", float("nan")),
            FakePhase("G", 10),
        ]
    )

    with pytest.raises(ValueError, match="finite"):
        phases_from_sumolib_program(program)
