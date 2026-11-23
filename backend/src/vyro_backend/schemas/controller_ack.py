from pydantic import Field

from .base import UTCDateTime, VYROSchema


class ControllerAck(VYROSchema):
    command_id: str = Field(min_length=1, max_length=128)
    intersection_id: str = Field(min_length=1, max_length=128)
    applied: bool
    reason: str = Field(min_length=1, max_length=256)
    timestamp: UTCDateTime
    schema_version: str = Field(default="v1.1", min_length=1, max_length=32)
