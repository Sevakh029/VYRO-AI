import json
import logging
import sqlite3
from collections.abc import Callable
from concurrent.futures import CancelledError, Future, ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock

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
                            schema_version TEXT
                        )
                        """
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
                self._initialized = True
                self.last_error = None
            except sqlite3.Error as exc:
                self.last_error = str(exc)
                logger.exception("Unable to initialize SQLite message logger")
                raise

    def log_message(self, topic: str, payload: bytes) -> int:
        self.initialize()
        received_at = self._received_at().astimezone(UTC).isoformat()
        schema_version = self._extract_schema_version(payload)
        try:
            with sqlite3.connect(self.database_path) as connection:
                connection.execute("PRAGMA busy_timeout = 5000")
                cursor = connection.execute(
                    """
                    INSERT INTO received_messages
                        (topic, payload, received_at, schema_version)
                    VALUES (?, ?, ?, ?)
                    """,
                    (topic, sqlite3.Binary(payload), received_at, schema_version),
                )
                if cursor.lastrowid is None:
                    raise RuntimeError("SQLite did not return an ID for the inserted message")
                return cursor.lastrowid
        except sqlite3.Error as exc:
            self.last_error = str(exc)
            logger.exception("Failed to persist MQTT message from topic %s", topic)
            raise

    def log_async(self, topic: str, payload: bytes) -> Future[int]:
        if self._closed:
            self._reopen()

        def persist() -> int:
            try:
                return self.log_message(topic, payload)
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
