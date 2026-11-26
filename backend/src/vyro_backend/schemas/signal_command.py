from pydantic import Field

from .base import UTCDateTime, VYROSchema


class SignalCommand(VYROSchema):
    command_id: str = Field(min_length=1, max_length=128)
    signal_id: str = Field(min_length=1, max_length=128)
    phase: int = Field(ge=0)
    hold_s: float = Field(gt=0, allow_inf_nan=False)
    reason: str = Field(min_length=1, max_length=256)
    ts_utc: UTCDateTime
    schema_version: str = Field(default="0.2", min_length=1, max_length=32)
