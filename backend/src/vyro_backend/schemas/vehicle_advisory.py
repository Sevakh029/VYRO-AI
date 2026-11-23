from pydantic import Field

from .base import UTCDateTime, VYROSchema


class VehicleAdvisory(VYROSchema):
    vehicle_id: str = Field(min_length=1, max_length=128)
    advisory_type: str = Field(min_length=1, max_length=64)
    message: str = Field(min_length=1, max_length=1024)
    timestamp: UTCDateTime
    schema_version: str = Field(default="v1.0", min_length=1, max_length=32)
