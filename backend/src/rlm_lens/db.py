from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import json
import sqlite3
import threading
from collections.abc import Iterator
from typing import Any, cast


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self._init_schema()

    @contextmanager
    def _locked(self) -> Iterator[None]:
        with self._lock:
            yield

    def close(self) -> None:
        with self._locked():
            self._conn.close()

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> None:
        with self._locked():
            self._conn.execute(sql, params)
            self._conn.commit()

    def executemany(self, sql: str, params: list[tuple[Any, ...]]) -> None:
        with self._locked():
            self._conn.executemany(sql, params)
            self._conn.commit()

    def fetchone(self, sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
        with self._locked():
            cursor = self._conn.execute(sql, params)
            return cast(sqlite3.Row | None, cursor.fetchone())

    def fetchall(self, sql: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        with self._locked():
            cursor = self._conn.execute(sql, params)
            return list(cursor.fetchall())

    def fetch_value(self, sql: str, params: tuple[Any, ...] = ()) -> Any | None:
        row = self.fetchone(sql, params)
        if row is None:
            return None
        return row[0]

    def _init_schema(self) -> None:
        with self._locked():
            self._conn.executescript(
                """
                PRAGMA journal_mode=WAL;

                CREATE TABLE IF NOT EXISTS corpora (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    root_path TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    index_config_json TEXT NOT NULL,
                    last_index_job_id TEXT,
                    last_indexed_at TEXT,
                    last_snapshot_hash TEXT,
                    latest_index_summary_json TEXT
                );

                CREATE TABLE IF NOT EXISTS files (
                    corpus_id TEXT NOT NULL,
                    path TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    bytes INTEGER NOT NULL,
                    mtime REAL NOT NULL,
                    is_binary INTEGER NOT NULL,
                    indexed_at TEXT NOT NULL,
                    language_hint TEXT,
                    PRIMARY KEY (corpus_id, path)
                );

                CREATE VIRTUAL TABLE IF NOT EXISTS file_fts USING fts5(
                    corpus_id UNINDEXED,
                    path,
                    content,
                    tokenize='unicode61'
                );

                CREATE TABLE IF NOT EXISTS index_jobs (
                    id TEXT PRIMARY KEY,
                    corpus_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    progress_json TEXT,
                    summary_json TEXT,
                    error_json TEXT
                );

                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    corpus_id TEXT NOT NULL,
                    snapshot_hash TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    runtime_config_json TEXT NOT NULL,
                    final_answer_md TEXT,
                    usage_json TEXT,
                    error_json TEXT
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS citations (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    corpus_id TEXT,
                    path TEXT NOT NULL,
                    start_line INTEGER NOT NULL,
                    end_line INTEGER NOT NULL,
                    snippet TEXT NOT NULL,
                    content_hash TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS trace_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    seq INTEGER NOT NULL,
                    ts TEXT NOT NULL,
                    type TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS exports (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    zip_path TEXT NOT NULL,
                    manifest_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS file_vectors (
                    corpus_id TEXT NOT NULL,
                    path TEXT NOT NULL,
                    vector_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (corpus_id, path)
                );

                CREATE TABLE IF NOT EXISTS index_watchers (
                    corpus_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    poll_interval_s INTEGER NOT NULL,
                    last_checked_at TEXT,
                    last_change_at TEXT,
                    fingerprint TEXT,
                    error_json TEXT
                );

                CREATE TABLE IF NOT EXISTS pii_findings (
                    id TEXT PRIMARY KEY,
                    corpus_id TEXT NOT NULL,
                    path TEXT NOT NULL,
                    line_no INTEGER NOT NULL,
                    category TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    preview TEXT NOT NULL,
                    found_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS eval_runs (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    config_json TEXT NOT NULL,
                    summary_json TEXT,
                    details_json TEXT,
                    error_json TEXT
                );
                """
            )
            self._ensure_column("citations", "corpus_id", "TEXT")
            self._conn.commit()

    def _ensure_column(self, table: str, column: str, definition: str) -> None:
        cursor = self._conn.execute(f"PRAGMA table_info({table})")
        existing = {str(row[1]) for row in cursor.fetchall()}
        if column in existing:
            return
        self._conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def set_setting(self, key: str, value: dict[str, Any]) -> None:
        payload = json.dumps(value)
        self.execute(
            "INSERT INTO settings (key, value_json) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json",
            (key, payload),
        )

    def get_setting(self, key: str) -> dict[str, Any] | None:
        row = self.fetchone("SELECT value_json FROM settings WHERE key = ?", (key,))
        if row is None:
            return None
        value = json.loads(str(row["value_json"]))
        return cast(dict[str, Any], value)
