from datetime import UTC, datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict


def validate_utc_timestamp(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("timestamp must be timezone-aware UTC")
    return value.astimezone(UTC)


UTCDateTime = Annotated[datetime, AfterValidator(validate_utc_timestamp)]


class VYROSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
