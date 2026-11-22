# Controller state and action contract

`SystemState` is the pure controller representation of one observed intersection.
Its fields match the v0.1 `IntersectionState` message:

| Controller field | v0.1 field | Meaning |
| --- | --- | --- |
| `intersection_id` | `intersection_id` | Stable signalized-intersection identifier |
| `phase_id` | `phase_id` | Currently observed phase |
| `time_in_phase_s` | `time_in_phase_s` | Elapsed time in that phase |
| `detector_counts` | `detector_counts` | Non-negative counts keyed by detector or approach ID |
| `timestamp` | `timestamp` | Timezone-aware UTC observation time |

`Action` mirrors the v0.1 `SignalCommand` fields: `intersection_id`, `phase_id`,
`reason`, and `timestamp`. It represents a requested phase, not proof that the
signal has already changed. The backend remains responsible for validating and
transporting the corresponding Pydantic message.

The controller does not consume vehicle coordinates or SUMO ground truth. Valid
phase IDs, minimum-green times, and yellow/all-red clearances come from trusted
intersection configuration and must be enforced before an action is emitted;
they cannot be inferred safely from a queue count alone.

The v0.1 state and command schemas have all fields needed for these two dataclasses,
so no message-schema change is currently required. A future configuration contract
may define signal-phase topology and timing constraints separately from live state.
