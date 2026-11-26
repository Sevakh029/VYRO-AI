"""UTC timestamp helpers shared by VYRO publishers."""

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(UTC)


def normalize_utc(timestamp: datetime) -> datetime:
    """Return a timezone-aware UTC timestamp, rejecting ambiguous naive values."""
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware UTC")
    return timestamp.astimezone(UTC)
