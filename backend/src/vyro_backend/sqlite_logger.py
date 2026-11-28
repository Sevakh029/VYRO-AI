import json
import logging
import sqlite3
from collections.abc import Callable
from concurrent.futures import CancelledError, Future, ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock

from .schemas import ControllerAck, SignalCommand

logger = logging.getLogger(__name__)


class SQLiteMessageLogger:
    def __init__(
        self,
        database_path: str | Path,
        received_at: Callable[[], datetime] | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        self._received_at = received_at or (lambda: datetime.now(UTC))
        self._executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="vyro-sqlite-logger",
        )
        self._closed = False
        self.last_error: str | None = None
        self._initialized = False
        self._initialization_lock = Lock()
        self.retention_limit = int(
            __import__("os").getenv("VYRO_LOG_RETENTION_LIMIT", "100000")
        )

    def initialize(self) -> None:
        if self._initialized:
            return
        with self._initialization_lock:
            if self._initialized:
                return
            try:
                self.database_path.parent.mkdir(parents=True, exist_ok=True)
                with sqlite3.connect(self.database_path) as connection:
                    connection.execute("PRAGMA busy_timeout = 5000")
                    connection.execute(
                        """
                        CREATE TABLE IF NOT EXISTS received_messages (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            topic TEXT NOT NULL,
                            payload BLOB NOT NULL,
                            received_at TEXT NOT NULL,
                            schema_version TEXT,
                            valid INTEGER NOT NULL DEFAULT 0,
                            error TEXT
                        )
                        """
                    )
                    columns = {
                        row[1]
                        for row in connection.execute(
                            "PRAGMA table_info(received_messages)"
                        ).fetchall()
                    }
                    if "valid" not in columns:
                        connection.execute(
                            "ALTER TABLE received_messages "
                            "ADD COLUMN valid INTEGER NOT NULL DEFAULT 0"
                        )
                    if "error" not in columns:
                        connection.execute(
                            "ALTER TABLE received_messages ADD COLUMN error TEXT"
                        )
                    connection.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_received_messages_topic
                        ON received_messages(topic)
                        """
                    )
                    connection.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_received_messages_received_at
                        ON received_messages(received_at)
                        """
                    )
                    connection.execute(
                        """
                        CREATE TABLE IF NOT EXISTS published_commands (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            command_id TEXT NOT NULL UNIQUE,
                            signal_id TEXT NOT NULL,
                            phase INTEGER NOT NULL,
                            hold_s REAL NOT NULL,
                            reason TEXT NOT NULL,
                            ts_utc TEXT NOT NULL,
                            published_at TEXT NOT NULL,
                            schema_version TEXT NOT NULL,
                            payload BLOB NOT NULL
                        )
                        """
                    )
                    connection.execute(
                        """
                        CREATE TABLE IF NOT EXISTS received_acknowledgments (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            command_id TEXT NOT NULL,
                            signal_id TEXT NOT NULL,
                            phase INTEGER NOT NULL,
                            hold_s REAL NOT NULL,
                            applied INTEGER NOT NULL,
                            reason TEXT NOT NULL,
                            ts_utc TEXT NOT NULL,
                            received_at TEXT NOT NULL,
                            schema_version TEXT NOT NULL,
                            payload BLOB NOT NULL,
                            UNIQUE (
                                command_id, ts_utc, applied, reason,
                                signal_id, phase, hold_s
                            )
                        )
                        """
                    )
                    connection.execute(
                        """
                        CREATE TABLE IF NOT EXISTS controller_decisions (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            signal_id TEXT NOT NULL,
                            timestamp TEXT NOT NULL,
                            state_phase INTEGER NOT NULL,
                            time_in_phase_s REAL NOT NULL,
                            pressure_per_phase TEXT NOT NULL,
                            decisions TEXT NOT NULL
                        )
                        """
                    )
                    connection.execute(
                        """
                        CREATE TABLE IF NOT EXISTS acknowledgement_statuses (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            command_id TEXT,
                            status TEXT NOT NULL,
                            reason TEXT NOT NULL,
                            payload TEXT NOT NULL,
                            timestamp TEXT NOT NULL
                        )
                        """
                    )
                self._initialized = True
                self.last_error = None
            except sqlite3.Error as exc:
                self.last_error = str(exc)
                logger.exception("Unable to initialize SQLite message logger")
                raise

    def log_message(
        self,
        topic: str,
        payload: bytes,
        *,
        valid: bool = False,
        error: str | None = None,
    ) -> int:
        self.initialize()
        timestamp = self._received_at()
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("received_at must be timezone-aware")
        received_at = timestamp.astimezone(UTC).isoformat()
        schema_version = self._extract_schema_version(payload)
        try:
            with sqlite3.connect(self.database_path) as connection:
                connection.execute("PRAGMA busy_timeout = 5000")
                cursor = connection.execute(
                    """
                    INSERT INTO received_messages
                        (topic, payload, received_at, schema_version, valid, error)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        topic,
                        sqlite3.Binary(payload),
                        received_at,
                        schema_version,
                        int(valid),
                        error,
                    ),
                )
                if cursor.lastrowid is None:
                    raise RuntimeError("SQLite did not return an ID for the inserted message")
                connection.execute(
                    """
                    DELETE FROM received_messages
                    WHERE id NOT IN (
                        SELECT id FROM received_messages
                        ORDER BY id DESC
                        LIMIT ?
                    )
                    """,
                    (max(1, self.retention_limit),),
                )
                return cursor.lastrowid
        except sqlite3.Error as exc:
            self.last_error = str(exc)
            logger.exception("Failed to persist MQTT message from topic %s", topic)
            raise

    def log_command(self, command: SignalCommand) -> int:
        self.initialize()
        published_at = datetime.now(UTC)
        payload = command.model_dump_json().encode("utf-8")
        try:
            with sqlite3.connect(self.database_path) as connection:
                connection.execute("PRAGMA busy_timeout = 5000")
                cursor = connection.execute(
                    """
                    INSERT OR IGNORE INTO published_commands
                        (command_id, signal_id, phase, hold_s, reason, ts_utc,
                         published_at, schema_version, payload)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        command.command_id,
                        command.signal_id,
                        command.phase,
                        command.hold_s,
                        command.reason,
                        command.ts_utc.astimezone(UTC).isoformat(),
                        published_at.isoformat(),
                        command.schema_version,
                        sqlite3.Binary(payload),
                    ),
                )
                del cursor
                row = connection.execute(
                    "SELECT id FROM published_commands WHERE command_id = ?",
                    (command.command_id,),
                ).fetchone()
                if row is None:
                    raise RuntimeError("SQLite did not persist published command")
                return int(row[0])
        except sqlite3.Error as exc:
            self.last_error = str(exc)
            logger.exception("Failed to persist published command %s", command.command_id)
            raise

    def log_acknowledgement(self, ack: ControllerAck) -> int:
        self.initialize()
        received_at = datetime.now(UTC)
        payload = ack.model_dump_json().encode("utf-8")
        try:
            with sqlite3.connect(self.database_path) as connection:
                connection.execute("PRAGMA busy_timeout = 5000")
                cursor = connection.execute(
                    """
                    INSERT OR IGNORE INTO received_acknowledgments
                        (command_id, signal_id, phase, hold_s, applied, reason,
                         ts_utc, received_at, schema_version, payload)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ack.command_id,
                        ack.signal_id,
                        ack.phase,
                        ack.hold_s,
                        int(ack.applied),
                        ack.reason,
                        ack.ts_utc.astimezone(UTC).isoformat(),
                        received_at.isoformat(),
                        ack.schema_version,
                        sqlite3.Binary(payload),
                    ),
                )
                del cursor
                row = connection.execute(
                    "SELECT id FROM received_acknowledgments WHERE command_id = ?",
                    (ack.command_id,),
                ).fetchone()
                if row is None:
                    raise RuntimeError("SQLite did not persist acknowledgment")
                return int(row[0])
        except sqlite3.Error as exc:
            self.last_error = str(exc)
            logger.exception("Failed to persist acknowledgment %s", ack.command_id)
            raise

    def log_decision(self, decision: dict[str, object]) -> int:
        self.initialize()
        try:
            with sqlite3.connect(self.database_path) as connection:
                connection.execute("PRAGMA busy_timeout = 5000")
                cursor = connection.execute(
                    """
                    INSERT INTO controller_decisions
                        (signal_id, timestamp, state_phase, time_in_phase_s,
                         pressure_per_phase, decisions)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(decision["signal_id"]),
                        str(decision["timestamp"]),
                        int(decision["state_phase"]),
                        float(decision["time_in_phase_s"]),
                        json.dumps(decision["pressure_per_phase"]),
                        json.dumps(decision["decisions"]),
                    ),
                )
                if cursor.lastrowid is None:
                    raise RuntimeError("SQLite did not persist controller decision")
                return cursor.lastrowid
        except sqlite3.Error as exc:
            self.last_error = str(exc)
            logger.exception("Failed to persist controller decision")
            raise

    def log_acknowledgement_status(self, status: dict[str, object]) -> int:
        self.initialize()
        ack = status.get("ack")
        command_id = (
            str(ack.get("command_id"))
            if isinstance(ack, dict) and ack.get("command_id") is not None
            else None
        )
        try:
            with sqlite3.connect(self.database_path) as connection:
                connection.execute("PRAGMA busy_timeout = 5000")
                cursor = connection.execute(
                    """
                    INSERT INTO acknowledgement_statuses
                        (command_id, status, reason, payload, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        command_id,
                        str(status["status"]),
                        str(status.get("reason", "")),
                        json.dumps(status),
                        datetime.now(UTC).isoformat(),
                    ),
                )
                if cursor.lastrowid is None:
                    raise RuntimeError("SQLite did not persist acknowledgement status")
                return cursor.lastrowid
        except sqlite3.Error as exc:
            self.last_error = str(exc)
            logger.exception("Failed to persist acknowledgement status")
            raise

    def log_command_async(self, command: SignalCommand) -> Future[int]:
        if self._closed:
            self._reopen()
        future = self._executor.submit(self.log_command, command)
        future.add_done_callback(
            lambda completed: self._report_async_failure(
                "vyro/v1/controller/command",
                completed,
            )
        )
        return future

    def log_acknowledgement_async(self, ack: ControllerAck) -> Future[int]:
        if self._closed:
            self._reopen()
        future = self._executor.submit(self.log_acknowledgement, ack)
        future.add_done_callback(
            lambda completed: self._report_async_failure(
                "vyro/v1/controller/ack",
                completed,
            )
        )
        return future

    def log_decision_async(self, decision: dict[str, object]) -> Future[int]:
        if self._closed:
            self._reopen()
        future = self._executor.submit(self.log_decision, decision)
        future.add_done_callback(
            lambda completed: self._report_async_failure(
                "vyro/v1/controller/decision",
                completed,
            )
        )
        return future

    def log_acknowledgement_status_async(
        self,
        status: dict[str, object],
    ) -> Future[int]:
        if self._closed:
            self._reopen()
        future = self._executor.submit(self.log_acknowledgement_status, status)
        future.add_done_callback(
            lambda completed: self._report_async_failure(
                "vyro/v1/controller/ack",
                completed,
            )
        )
        return future

    def log_async(
        self,
        topic: str,
        payload: bytes,
        *,
        valid: bool = False,
        error: str | None = None,
    ) -> Future[int]:
        if self._closed:
            self._reopen()

        def persist() -> int:
            try:
                return self.log_message(topic, payload, valid=valid, error=error)
            except sqlite3.Error as exc:
                raise exc

        future = self._executor.submit(persist)
        future.add_done_callback(
            lambda completed: self._report_async_failure(topic, completed)
        )
        return future

    def _reopen(self) -> None:
        self._executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="vyro-sqlite-logger",
        )
        self._closed = False
        self._initialized = False

    def _report_async_failure(self, topic: str, future: Future[int]) -> None:
        try:
            future.result()
        except CancelledError:
            logger.error("SQLite persistence task was cancelled for topic %s", topic)
        except Exception as exc:
            self.last_error = str(exc)
            if not isinstance(exc, sqlite3.Error):
                logger.exception(
                    "SQLite persistence task failed for topic %s",
                    topic,
                    exc_info=(type(exc), exc, exc.__traceback__),
                )

    def flush(self, timeout: float | None = None) -> None:
        future = self._executor.submit(lambda: None)
        future.result(timeout=timeout)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._executor.shutdown(wait=True, cancel_futures=False)

    @staticmethod
    def _extract_schema_version(payload: bytes) -> str | None:
        try:
            data = json.loads(payload)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None
        if not isinstance(data, dict):
            return None
        for key in ("schema_version", "schemaVersion"):
            value = data.get(key)
            if isinstance(value, (str, int, float)):
                return str(value)
        return None
