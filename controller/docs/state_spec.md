# Controller state and action contract

`SystemState` is the pure controller representation of one observed intersection.
Its fields match the v0.2 `IntersectionState` message:

| Controller field | v0.2 field | Meaning |
| --- | --- | --- |
| `intersection_id` | `intersection_id` | Stable signalized-intersection identifier |
| `phase_id` | `phase_id` | Currently observed phase |
| `time_in_phase_s` | `time_in_phase_s` | Elapsed time in that phase |
| `detector_counts` | `detector_counts` | Non-negative counts keyed by detector or approach ID |
| `timestamp` | `timestamp` | Timezone-aware UTC observation time |
| `schema_version` | `schema_version` | Version of the public message contract |

`vyro_controller.state.Action` is the state-shaped adapter type. The pressure
policy used by `decide()` returns `vyro_controller.types.Action`, which contains
`signal_id`, `phase`, `hold_s`, and `reason`; the backend orchestrator translates
it to a `SignalCommand`. Neither action type proves that a signal has already
changed.

The controller does not consume vehicle coordinates or SUMO ground truth. Valid
phase IDs, minimum-green times, and yellow/all-red clearances come from trusted
intersection configuration and must be enforced before an action is emitted;
they cannot be inferred safely from a queue count alone.

The v0 estimator accepts map-matched probe observations containing an approach,
distance to its stop line, and speed. It considers stopped probes within 50 m of
the stop line and takes the greater of that count and the supplied approach
count, avoiding duplicate addition when both sources observe the same queue.
This is a simple v0 estimate, not a calibrated queue-length model. `decide()`
emits controller `Action` values only for configured observed phases and
rechecks each selected phase through the safety layer; an unknown observed phase
produces no action.

The v0.2 state schema has all fields needed by `SystemState`, and the controller
action is translated to the existing command schema, so no message-schema change
is currently required. A future configuration contract may define signal-phase
topology and timing constraints separately from live state.
