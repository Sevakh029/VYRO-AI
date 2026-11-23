from pydantic import Field

from .base import UTCDateTime, VYROSchema


class SignalCommand(VYROSchema):
    intersection_id: str = Field(min_length=1, max_length=128)
    phase_id: int = Field(ge=0)
    reason: str = Field(min_length=1, max_length=256)
    timestamp: UTCDateTime
    schema_version: str = Field(default="v1.1", min_length=1, max_length=32)
    command_id: str | None = Field(default=None, min_length=1, max_length=128)
