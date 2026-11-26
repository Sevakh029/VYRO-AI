# VYRO interface contracts

This document is the baseline for cross-component message and experiment
contracts. MQTT payloads are UTF-8 JSON, use `schema_version`, and use the
`vyro/v1/` topic namespace. MQTT publish and subscribe operations use QoS 1.

## MQTT topics

| Topic | Direction | Message |
| --- | --- | --- |
| `vyro/v1/vehicle/state` | vehicle/bridge -> backend | `VehicleState` |
| `vyro/v1/intersection/state` | bridge -> backend | `IntersectionState` |
| `vyro/v1/controller/command` | backend -> bridge | `SignalCommand` |
| `vyro/v1/controller/ack` | bridge -> backend | `ControllerAck` |
| `vyro/v1/vehicle/advisory` | backend/agent -> vehicle/dashboard | `VehicleAdvisory` |
| `vyro/v1/preemption/request` | controller -> bridge | `PreemptionRequest` |
| `vyro/v1/metrics/snapshot` | backend -> dashboard | `MetricsSnapshot` |

`vyro/v1/vehicle/advisory` is the single advisory topic. Identify the target
vehicle in the `VehicleAdvisory.vehicle_id` payload field; do not create a
separate topic per vehicle or publish advisories on an unversioned topic.

## Signal commands and acknowledgements

`SignalCommand` requests a phase for one configured signal. All listed fields
are required. `ControllerAck` reports whether that exact request was applied
and echoes its identifying and requested-value fields.

| Field | `SignalCommand` | `ControllerAck` | Contract |
| --- | --- | --- | --- |
| `command_id` | required | required | Non-empty unique command identifier; the acknowledgement must match the request. |
| `signal_id` | required | required | Stable ID of the controlled signal; the acknowledgement must match the request. |
| `phase` | required | required | Configured phase identifier; the acknowledgement must match the request. |
| `hold_s` | required | required | Finite positive duration in seconds; the acknowledgement reports the requested duration. |
| `applied` | — | required | Boolean indicating whether the command was applied. |
| `reason` | required | required | Non-empty explanation/category for the command or its outcome; explain rejection when `applied` is false. |
| `ts_utc` | required | required | UTC timestamp for command creation or acknowledgement, respectively. |
| `schema_version` | required | required | Message schema version. |

An acknowledgement with `applied: false` is not a successful phase change.
Timeouts or missing acknowledgements must not be interpreted as proof that a
command was applied. Command handling must remain subject to the signal's
configured phase and safety constraints.

## Required phase configuration per signal

Before a signal can receive commands, its trusted configuration must define:

- its stable `signal_id`;
- the complete set of valid phase identifiers for that signal;
- for every phase, a positive minimum green duration;
- the yellow and all-red clearance durations required when transitioning from
  that phase; and
- the permitted phase-transition/conflict relationships needed to ensure that
  conflicting movements are never given green simultaneously.

Reject a command for an unknown signal or unconfigured phase. Enforce minimum
green and required yellow/all-red clearance during transitions; `hold_s` does
not override those safety constraints. Do not infer valid phases, movement
conflicts, or clearance timings from live traffic state.

## UTC timestamps

All wire timestamps are ISO 8601 UTC strings ending in `Z`, for example
`2026-11-20T10:00:00Z`. Timestamps must identify an actual UTC instant; do not
send naive datetimes or local-time offsets. Internal wall-clock experiment and
state timestamps must also be timezone-aware UTC.

## Random seed rules

Use the reserved controller seeds from
`controller/src/vyro_controller/seeds.py`:

- `TUNING_SEEDS = (1, 2, 3, 4, 5)` for tuning only.
- `TEST_SEEDS = (100, 101, 102, 103, 104, 105, 106, 107, 108, 109)` for tests
  and held-out evaluation.

The sets must remain disjoint. Never tune on test seeds or report evaluation
results as held-out results if those seeds were used for tuning. Record the
seed used so an experiment can be reproduced.

## Contract evolution

This document establishes the baseline for subsequent changes. Make changes
additively: preserve existing topic names, field meanings, and compatibility.
New optional fields or new topics may be added without changing existing
behavior. A change that removes, renames, or changes the meaning or requiredness
of a field is breaking and requires an explicitly coordinated versioned
migration; it is not an additive change.

The current backend v0.2 command and acknowledgement models still use
`intersection_id`, `phase_id`, and `timestamp`, and the command model does not
yet include `hold_s`. The advisory publisher also currently emits a per-vehicle,
unversioned topic. Those implementations do not yet conform to the baseline
above; align them before claiming wire-contract conformance.
