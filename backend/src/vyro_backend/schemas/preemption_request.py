from pydantic import Field

from .base import UTCDateTime, VYROSchema


class PreemptionRequest(VYROSchema):
    intersection_id: str = Field(min_length=1, max_length=128)
    vehicle_id: str = Field(min_length=1, max_length=128)
    lead_time_s: float = Field(gt=0, allow_inf_nan=False)
    state: str = Field(default="requested", pattern="^(requested|granted|cleared)$")
    timestamp: UTCDateTime
    schema_version: str = Field(default="0.2", min_length=1, max_length=32)
