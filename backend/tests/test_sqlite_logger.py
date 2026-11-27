import json
import sqlite3
from datetime import UTC, datetime

import pytest
from vyro_backend.message_handler import MQTTMessageHandler
from vyro_backend.schemas import ControllerAck, SignalCommand
from vyro_backend.sqlite_logger import SQLiteMessageLogger
from vyro_backend.websocket_manager import WebSocketManager

UTC_TIMESTAMP = datetime(2026, 11, 22, 16, 30, tzinfo=UTC)


def test_database_initializes_and_stores_received_message(tmp_path) -> None:
    database = tmp_path / "messages.db"
    logger = SQLiteMessageLogger(database, received_at=lambda: UTC_TIMESTAMP)
    payload = b'{"vehicle_id":"vehicle-1","schema_version":"0.2"}'

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
        "0.2",
    )


def test_multiple_messages_and_topics_are_separate_records(tmp_path) -> None:
    database = tmp_path / "messages.db"
    logger = SQLiteMessageLogger(database, received_at=lambda: UTC_TIMESTAMP)

    logger.log_async(
        "vyro/v1/vehicle/state",
        b'{"vehicle_id":"vehicle-1","schemaVersion":"v1.0"}',
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
    assert bytes(rows[0][1]) == b'{"vehicle_id":"vehicle-1","schemaVersion":"v1.0"}'
    assert bytes(rows[1][1]) == b'{"vehicle_id":"vehicle-2"}'
    assert bytes(rows[2][1]) == b'{"intersection_id":"intersection-1"}'
    assert all(row[2] == UTC_TIMESTAMP.isoformat() for row in rows)
    assert rows[0][3] == "v1.0"
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


def test_logger_retains_only_configured_number_of_messages(tmp_path) -> None:
    logger = SQLiteMessageLogger(tmp_path / "messages.db")
    logger.retention_limit = 3

    for index in range(5):
        logger.log_async(
            "vyro/v1/vehicle/state",
            f'{{"vehicle_id":"vehicle-{index}"}}'.encode(),
        )
    logger.flush(timeout=5)

    with sqlite3.connect(tmp_path / "messages.db") as connection:
        rows = connection.execute(
            "SELECT payload FROM received_messages ORDER BY id"
        ).fetchall()

    logger.close()
    assert len(rows) == 3


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
            "SELECT topic, payload, valid, error FROM received_messages ORDER BY id"
        ).fetchall()
    logger.close()

    assert len(rows) == 3
    assert rows[0][0] == "vyro/v1/vehicle/state"
    assert bytes(rows[0][1]) == valid
    assert rows[0][2:] == (1, None)
    assert bytes(rows[1][1]) == b"{malformed"
    assert rows[1][2:] == (0, "schema validation failed")
    assert bytes(rows[2][1]) == b"unknown payload"
    assert rows[2][2:] == (0, "unsupported topic")


def test_logger_rejects_naive_received_at(tmp_path) -> None:
    logger = SQLiteMessageLogger(
        tmp_path / "naive.db",
        received_at=lambda: datetime(2026, 11, 22, 16, 30),
    )

    with pytest.raises(ValueError, match="timezone-aware"):
        logger.log_message("vyro/v1/vehicle/state", b"payload")

    logger.close()


def test_logger_migrates_preexisting_message_table(tmp_path) -> None:
    database = tmp_path / "previous-schema.db"
    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            CREATE TABLE received_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                payload BLOB NOT NULL,
                received_at TEXT NOT NULL,
                schema_version TEXT
            )
            """
        )

    logger = SQLiteMessageLogger(database)
    logger.log_message("vyro/v1/vehicle/state", b"payload", valid=True)
    logger.close()

    with sqlite3.connect(database) as connection:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(received_messages)")
        }
        row = connection.execute(
            "SELECT valid, error FROM received_messages"
        ).fetchone()

    assert {"valid", "error"} <= columns
    assert row == (1, None)


def test_rate_limited_message_is_logged_as_invalid(tmp_path, monkeypatch) -> None:
    logger = SQLiteMessageLogger(tmp_path / "rate-limited.db")
    handler = MQTTMessageHandler(WebSocketManager(), logger)
    monkeypatch.setattr(handler.rate_limiter, "allow", lambda: False)

    assert handler("vyro/v1/vehicle/state", b"payload") is False
    logger.flush(timeout=5)

    with sqlite3.connect(tmp_path / "rate-limited.db") as connection:
        row = connection.execute(
            "SELECT valid, error FROM received_messages"
        ).fetchone()
    logger.close()

    assert row == (0, "rate limit exceeded")


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


def test_command_acknowledgement_correlation_and_duplicate_deduplication(tmp_path) -> None:
    database = tmp_path / "commands.db"
    logger = SQLiteMessageLogger(database)
    timestamp = datetime(2026, 11, 22, 16, 30, tzinfo=UTC)
    command = SignalCommand(
        command_id="command-1",
        signal_id="signal-1",
        phase=2,
        hold_s=15.0,
        reason="queue_pressure",
        ts_utc=timestamp,
    )
    applied = ControllerAck(
        command_id="command-1",
        signal_id="signal-1",
        phase=2,
        hold_s=15.0,
        applied=True,
        reason="phase applied",
        ts_utc=timestamp,
    )

    command_id = logger.log_command(command)
    ack_id = logger.log_acknowledgement(applied)
    duplicate_ack_id = logger.log_acknowledgement(applied)

    with sqlite3.connect(database) as connection:
        command_row = connection.execute(
            """
            SELECT command_id, signal_id, phase, hold_s
            FROM published_commands WHERE id = ?
            """,
            (command_id,),
        ).fetchone()
        ack_row = connection.execute(
            """
            SELECT command_id, applied, reason
            FROM received_acknowledgments WHERE id = ?
            """,
            (ack_id,),
        ).fetchone()
        ack_count = connection.execute(
            "SELECT COUNT(*) FROM received_acknowledgments"
        ).fetchone()[0]

    logger.close()
    assert command_row == ("command-1", "signal-1", 2, 15.0)
    assert ack_row == ("command-1", 1, "phase applied")
    assert ack_id == duplicate_ack_id
    assert ack_count == 1


def test_rejected_acknowledgement_is_stored_separately(tmp_path) -> None:
    database = tmp_path / "rejected.db"
    logger = SQLiteMessageLogger(database)
    timestamp = datetime(2026, 11, 22, 16, 30, tzinfo=UTC)
    rejected = ControllerAck(
        command_id="command-rejected",
        signal_id="signal-1",
        phase=1,
        hold_s=10.0,
        applied=False,
        reason="invalid phase",
        ts_utc=timestamp,
    )

    record_id = logger.log_acknowledgement(rejected)

    with sqlite3.connect(database) as connection:
        row = connection.execute(
            """
            SELECT command_id, applied, reason
            FROM received_acknowledgments WHERE id = ?
            """,
            (record_id,),
        ).fetchone()

    logger.close()
    assert row == ("command-rejected", 0, "invalid phase")
