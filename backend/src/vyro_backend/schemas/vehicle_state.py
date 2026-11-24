from typing import Literal

from pydantic import Field

from .base import UTCDateTime, VYROSchema


class VehicleState(VYROSchema):
    vehicle_id: str = Field(min_length=1, max_length=128)
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)
    speed_mps: float = Field(ge=0, allow_inf_nan=False)
    heading_deg: float = Field(default=0, ge=0, lt=360, allow_inf_nan=False)
    timestamp: UTCDateTime
    schema_version: str = Field(default="0.2", min_length=1, max_length=32)
    vehicle_type: Literal["car", "minibus", "truck", "emergency", "unknown"] = "unknown"
