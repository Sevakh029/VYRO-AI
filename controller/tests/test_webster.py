import pytest
from vyro_controller.webster import PhaseFlow, calculate_webster_plan


def test_webster_cycle_and_splits_follow_critical_flow_ratios() -> None:
    plan = calculate_webster_plan(
        [
            PhaseFlow(0, 360, 1800, minimum_green_s=5, clearance_s=4),
            PhaseFlow(1, 540, 1800, minimum_green_s=5, clearance_s=4),
        ]
    )

    assert plan.cycle_length_s == pytest.approx(34)
    assert plan.lost_time_s == pytest.approx(8)
    assert [split.green_s for split in plan.green_splits] == pytest.approx([10.4, 15.6])
    assert sum(split.green_s for split in plan.green_splits) + plan.lost_time_s == pytest.approx(
        plan.cycle_length_s
    )
    assert plan.oversaturated is False


def test_zero_flow_uses_equal_splits_and_retains_clearance_and_minimum_green() -> None:
    plan = calculate_webster_plan(
        [
            PhaseFlow(0, 0, 1800, minimum_green_s=7, clearance_s=4),
            PhaseFlow(1, 0, 1800, minimum_green_s=7, clearance_s=4),
        ]
    )

    assert plan.cycle_length_s == pytest.approx(30)
    assert [split.green_s for split in plan.green_splits] == pytest.approx([11, 11])
    assert all(split.green_s >= 7 for split in plan.green_splits)


def test_oversaturated_flow_uses_maximum_cycle_without_violating_minimum_green() -> None:
    plan = calculate_webster_plan(
        [
            PhaseFlow(0, 1200, 1800, minimum_green_s=8, clearance_s=3),
            PhaseFlow(1, 900, 1800, minimum_green_s=8, clearance_s=3),
        ],
        max_cycle_s=90,
    )

    assert plan.oversaturated is True
    assert plan.cycle_length_s == pytest.approx(90)
    assert [split.green_s for split in plan.green_splits] == pytest.approx([48, 36])
    assert all(split.green_s >= 8 for split in plan.green_splits)


def test_minimum_green_floor_is_redistributed_from_zero_flow_phases() -> None:
    plan = calculate_webster_plan(
        [
            PhaseFlow(0, 1000, 1800, minimum_green_s=5, clearance_s=2),
            PhaseFlow(1, 0, 1800, minimum_green_s=15, clearance_s=2),
        ]
    )

    assert [split.green_s for split in plan.green_splits] == pytest.approx([11, 15])
    assert sum(split.green_s for split in plan.green_splits) + plan.lost_time_s == pytest.approx(
        plan.cycle_length_s
    )


def test_rejects_duplicate_phases_and_infeasible_minimum_greens() -> None:
    phase = PhaseFlow(0, 100, 1800, minimum_green_s=10, clearance_s=5)

    with pytest.raises(ValueError, match="unique"):
        calculate_webster_plan([phase, phase])
    with pytest.raises(ValueError, match="exceed max_cycle_s"):
        calculate_webster_plan(
            [phase, PhaseFlow(1, 100, 1800, minimum_green_s=10, clearance_s=5)],
            min_cycle_s=20,
            max_cycle_s=29,
        )


def test_rejects_invalid_flow_and_cycle_values() -> None:
    with pytest.raises(ValueError, match="saturation_flow"):
        PhaseFlow(0, 10, 0)
    with pytest.raises(ValueError, match="min_cycle_s"):
        calculate_webster_plan([PhaseFlow(0, 10, 1800)], min_cycle_s=float("nan"))


def test_large_finite_flows_do_not_overflow_green_allocation() -> None:
    plan = calculate_webster_plan(
        [
            PhaseFlow(0, 1e307, 1),
            PhaseFlow(1, 1e307, 1),
        ],
        max_cycle_s=90,
    )

    assert plan.oversaturated is True
    assert [split.green_s for split in plan.green_splits] == pytest.approx([45, 45])
