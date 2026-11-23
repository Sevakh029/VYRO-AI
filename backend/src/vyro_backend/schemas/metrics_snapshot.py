from pydantic import Field

from .base import UTCDateTime, VYROSchema


class MetricsSnapshot(VYROSchema):
    vehicle_count: int = Field(ge=0)
    mean_speed_mps: float = Field(ge=0, allow_inf_nan=False)
    stopped_vehicle_count: int = Field(ge=0)
    timestamp: UTCDateTime
    schema_version: str = Field(default="v0.2", min_length=1, max_length=32)
