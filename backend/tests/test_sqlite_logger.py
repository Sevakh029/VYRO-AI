import json
import sqlite3
from datetime import UTC, datetime

import pytest
from vyro_backend.message_handler import MQTTMessageHandler
from vyro_backend.sqlite_logger import SQLiteMessageLogger
from vyro_backend.websocket_manager import WebSocketManager


UTC_TIMESTAMP = datetime(2026, 11, 22, 16, 30, tzinfo=UTC)


def test_database_initializes_and_stores_received_message(tmp_path) -> None:
    database = tmp_path / "messages.db"
    logger = SQLiteMessageLogger(database, received_at=lambda: UTC_TIMESTAMP)
    payload = b'{"vehicle_id":"vehicle-1","schema_version":"v0.2"}'

    record_id = logger.log_message("vyro/v1/vehicle/state", payload)
    logger.close()

    with sqlite3.connect(database) as connection:
        row = connection.execute(
            """
            SELECT id, topic, payload, received_at, schema_version
            FROM received_messages
            WHERE id = ?
            """,
            (record_id,),
        ).fetchone()

    assert row == (
        record_id,
        "vyro/v1/vehicle/state",
        payload,
        UTC_TIMESTAMP.isoformat(),
        "v0.2",
    )


def test_multiple_messages_and_topics_are_separate_records(tmp_path) -> None:
    database = tmp_path / "messages.db"
    logger = SQLiteMessageLogger(database, received_at=lambda: UTC_TIMESTAMP)

    logger.log_async(
        "vyro/v1/vehicle/state",
        b'{"vehicle_id":"vehicle-1","schemaVersion":"v0.2"}',
    )
    logger.log_async(
        "vyro/v1/vehicle/state",
        b'{"vehicle_id":"vehicle-2"}',
    )
    logger.log_async(
        "vyro/v1/intersection/state",
        b'{"intersection_id":"intersection-1"}',
    )
    logger.flush(timeout=5)

    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            """
            SELECT topic, payload, received_at, schema_version
            FROM received_messages
            ORDER BY id
            """
        ).fetchall()

    logger.close()

    assert len(rows) == 3
    assert [row[0] for row in rows] == [
        "vyro/v1/vehicle/state",
        "vyro/v1/vehicle/state",
        "vyro/v1/intersection/state",
    ]
    assert bytes(rows[0][1]) == b'{"vehicle_id":"vehicle-1","schemaVersion":"v0.2"}'
    assert bytes(rows[1][1]) == b'{"vehicle_id":"vehicle-2"}'
    assert bytes(rows[2][1]) == b'{"intersection_id":"intersection-1"}'
    assert all(row[2] == UTC_TIMESTAMP.isoformat() for row in rows)
    assert rows[0][3] == "v0.2"
    assert rows[1][3] is None


def test_malformed_payload_is_preserved_with_no_schema_version(tmp_path) -> None:
    database = tmp_path / "messages.db"
    logger = SQLiteMessageLogger(database)
    payload = b"{malformed"

    logger.log_async("vyro/v1/vehicle/state", payload)
    logger.flush(timeout=5)

    with sqlite3.connect(database) as connection:
        row = connection.execute(
            "SELECT payload, schema_version FROM received_messages"
        ).fetchone()

    logger.close()
    assert bytes(row[0]) == payload
    assert row[1] is None


def test_restart_preserves_existing_records(tmp_path) -> None:
    database = tmp_path / "messages.db"
    first = SQLiteMessageLogger(database)
    first.log_async(
        "vyro/v1/vehicle/state",
        b'{"vehicle_id":"vehicle-before-restart"}',
    )
    first.flush(timeout=5)
    first.close()

    second = SQLiteMessageLogger(database)
    second.log_async(
        "vyro/v1/vehicle/state",
        b'{"vehicle_id":"vehicle-after-restart"}',
    )
    second.flush(timeout=5)

    with sqlite3.connect(database) as connection:
        payloads = [
            bytes(row[0])
            for row in connection.execute(
                "SELECT payload FROM received_messages ORDER BY id"
            ).fetchall()
        ]

    second.close()
    assert payloads == [
        b'{"vehicle_id":"vehicle-before-restart"}',
        b'{"vehicle_id":"vehicle-after-restart"}',
    ]


def test_logger_can_reopen_after_close(tmp_path) -> None:
    logger = SQLiteMessageLogger(tmp_path / "messages.db")
    logger.close()

    future = logger.log_async(
        "vyro/v1/vehicle/state",
        b'{"vehicle_id":"after-reopen"}',
    )
    assert future.result(timeout=5) > 0
    logger.close()


def test_message_handler_logs_before_validation_and_preserves_messages(tmp_path) -> None:
    database = tmp_path / "messages.db"
    logger = SQLiteMessageLogger(database)
    handler = MQTTMessageHandler(WebSocketManager(), logger)

    valid = json.dumps(
        {
            "vehicle_id": "vehicle-1",
            "latitude": 40.18,
            "longitude": 44.51,
            "speed_mps": 12.5,
            "timestamp": UTC_TIMESTAMP.isoformat(),
        }
    ).encode()
    assert handler("vyro/v1/vehicle/state", valid) == "vehicle-1"
    assert handler("vyro/v1/vehicle/state", b"{malformed") is False
    assert handler("vyro/v1/unknown", b"unknown payload") is False
    logger.flush(timeout=5)

    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            "SELECT topic, payload FROM received_messages ORDER BY id"
        ).fetchall()
    logger.close()

    assert len(rows) == 3
    assert rows[0][0] == "vyro/v1/vehicle/state"
    assert bytes(rows[0][1]) == valid
    assert bytes(rows[1][1]) == b"{malformed"
    assert bytes(rows[2][1]) == b"unknown payload"


def test_database_error_is_reported_and_raised(tmp_path, monkeypatch, caplog) -> None:
    database = tmp_path / "messages.db"
    logger = SQLiteMessageLogger(database)

    def fail_connect(*args, **kwargs):
        del args, kwargs
        raise sqlite3.OperationalError("database unavailable")

    monkeypatch.setattr(sqlite3, "connect", fail_connect)

    with pytest.raises(sqlite3.OperationalError, match="database unavailable"):
        logger.log_message("vyro/v1/vehicle/state", b"payload")

    assert "Unable to initialize SQLite message logger" in caplog.text
    assert logger.last_error == "database unavailable"
    logger.close()


def test_async_database_error_is_reported(tmp_path, monkeypatch, caplog) -> None:
    database = tmp_path / "messages.db"
    logger = SQLiteMessageLogger(database)

    def fail_connect(*args, **kwargs):
        del args, kwargs
        raise sqlite3.OperationalError("database unavailable")

    monkeypatch.setattr(sqlite3, "connect", fail_connect)
    future = logger.log_async("vyro/v1/vehicle/state", b"payload")

    with pytest.raises(sqlite3.OperationalError, match="database unavailable"):
        future.result(timeout=5)

    assert logger.last_error == "database unavailable"
    assert "Unable to initialize SQLite message logger" in caplog.text
    logger.close()
