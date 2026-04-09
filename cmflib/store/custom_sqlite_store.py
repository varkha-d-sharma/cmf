import json
import os
import sqlite3
import time
import typing as t


class CustomSqliteStore:
    """Store immutable execution records in a separate client-side SQLite DB."""

    def __init__(self, db_path: str):
        self.db_path = self._resolve_db_path(db_path)
        self._init_db()

    @staticmethod
    def _resolve_db_path(path_hint: str) -> str:
        # If a directory is provided, store metadata in an mlmd file in that directory.
        if os.path.isdir(path_hint):
            return os.path.join(path_hint, "mlmd")

        # Use the exact filepath provided by caller.
        return path_hint

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def _init_db(self) -> None:
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS execution_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_uuid TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    UNIQUE(execution_uuid)
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_execution_log_created_at
                ON execution_log (created_at)
                """
            )
            conn.commit()

    def insert_execution_log(
        self,
        execution_uuid: str,
        metadata: t.Optional[t.Dict[str, t.Any]] = None,
    ) -> None:
        payload = json.dumps(metadata or {}, default=str, sort_keys=True)
        now_ms = int(time.time() * 1000)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO execution_log (
                    execution_uuid,
                    metadata_json,
                    created_at
                ) VALUES (?, ?, ?)
                """,
                (
                    execution_uuid,
                    payload,
                    now_ms,
                ),
            )
            conn.commit()