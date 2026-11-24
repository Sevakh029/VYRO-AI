# Schema v0.1 to v0.2 field changes

The controller/SystemState and IntersectionState field sets are unchanged from
the v0.1 contract. The `schema_version` field changes to `"0.2"` across every
message model.

Required field changes:

| Area | Change | Status |
|---|---|---|
| all public models | normalize `schema_version` default to `"0.2"` | applied |
| VehicleAdvisory | stable topic `vyro/v1/vehicle/advisory` | applied |
| MetricsSnapshot | stable topic `vyro/v1/metrics/snapshot` | applied |
| ControllerAck | add Pydantic model and support topic | applied |
| SystemState / Action | retain existing UTC-aware dataclass fields | no field change |

This is an additive v0.2 change set. No field required by P2 was removed.
