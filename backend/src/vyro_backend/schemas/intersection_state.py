from pydantic import Field

from .base import UTCDateTime, VYROSchema


class IntersectionState(VYROSchema):
    intersection_id: str = Field(min_length=1, max_length=128)
    phase_id: int = Field(ge=0)
    time_in_phase_s: float = Field(ge=0, allow_inf_nan=False)
    detector_counts: dict[str, int] = Field(default_factory=dict)
    timestamp: UTCDateTime
    schema_version: str = Field(default="0.2", min_length=1, max_length=32)
