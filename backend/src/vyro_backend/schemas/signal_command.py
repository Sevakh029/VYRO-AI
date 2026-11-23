from pydantic import Field

from .base import UTCDateTime, VYROSchema


class SignalCommand(VYROSchema):
    intersection_id: str = Field(min_length=1, max_length=128)
    phase_id: int = Field(ge=0)
    reason: str = Field(min_length=1, max_length=256)
    timestamp: UTCDateTime
    schema_version: str = Field(default="v0.2", min_length=1, max_length=32)
