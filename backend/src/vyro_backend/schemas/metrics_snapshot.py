from pydantic import Field

from .base import UTCDateTime, VYROSchema


class MetricsSnapshot(VYROSchema):
    vehicle_count: int = Field(ge=0)
    mean_speed_mps: float = Field(ge=0, allow_inf_nan=False)
    stopped_vehicle_count: int = Field(ge=0)
    timestamp: UTCDateTime
