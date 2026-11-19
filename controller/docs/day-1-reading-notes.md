# P2 Day 1 Reading Notes

## Webster fixed-time control

Webster's method provides a deterministic baseline for an isolated signalized
intersection. It first estimates the cycle length from the critical approach flows:

`C = (1.5 * L + 5) / (1 - Y)`

where `L` is the lost time from phase transitions and `Y` is the sum of the critical
flow ratios (demand divided by saturation flow). Each phase receives a green split
proportional to its critical flow ratio, while minimum green time and the
intersection's all-red requirements remain hard constraints.

The method is simple and reproducible, but it assumes known, steady demand and does
not react when a real-time queue or incident changes approach pressure. It is most
valuable as a fair, calibrated baseline rather than as the final adaptive policy.

## SUMO actuated control

SUMO actuated control extends phase logic with detectors and real-time demand. A
phase can be extended when a detector reports approaching vehicles, subject to
minimum-green and maximum-green settings. It is more responsive than fixed-time
control and is a useful second baseline. It also operates locally unless the signal
program is coordinated or manually extended across intersections.

## Max-pressure control

Max-pressure control chooses a phase by comparing queue or occupancy on incoming
lanes with demand on outgoing lanes. A phase has a larger pressure when it can serve
a large incoming queue while preserving capacity downstream. The selected phase
should be the admissible phase with the highest weighted pressure, with switching
penalties and starvation protections.

For VYRO, this is a reasonable starting point because it is model-light, can operate
from aggregated estimates instead of private ground-truth vehicle data, and can be
expressed as a pure `decide(state) -> actions` library. Neighbor pressures can later
add local spillback awareness.

## Safety model

The initial controller must be constrained rather than optimized freely:

- only valid predefined phases may be selected;
- minimum green time must complete before switching;
- yellow and all-red clearance must be guaranteed;
- maximum waiting time bounds starvation on an approach;
- pedestrian guarantees, when added, must retain a safe clearance interval;
- invalid or stale state must trigger a fixed-time or existing-program fallback.

These rules are safety invariants, separate from traffic optimization.

## Baseline and measurement decision

P2 will use fixed-time Webster plans as the primary design baseline, SUMO actuated
control as the infrastructure baseline, and queue/pressure control as the first
adaptive controller. Tuning will use only `TUNING_SEEDS`; `TEST_SEEDS` remain
untouched until final evaluation.

Success will be reported as relative change in travel time, waiting time, queue
length, throughput, and congestion-duration metrics against the baselines. Honest
negative results and failure cases will remain in the results rather than being
excluded.
