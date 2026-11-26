from datetime import UTC, datetime, timezone

import pytest

from vyro_backend.timestamps import normalize_utc, utc_now


def test_utc_now_is_timezone_aware_and_utc() -> None:
    timestamp = utc_now()

    assert timestamp.tzinfo is UTC
    assert timestamp.utcoffset() == UTC.utcoffset(timestamp)


def test_normalize_utc_converts_offset_timestamp_to_utc() -> None:
    timestamp = datetime(2026, 11, 24, 12, tzinfo=timezone.utc)

    assert normalize_utc(timestamp) == timestamp


def test_normalize_utc_rejects_naive_timestamp() -> None:
    with pytest.raises(ValueError, match="timezone-aware UTC"):
        normalize_utc(datetime(2026, 11, 24, 12))
