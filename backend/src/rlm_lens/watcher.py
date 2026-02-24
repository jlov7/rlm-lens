from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
from typing import Any

from .db import Database
from .indexer import Indexer
from .models import IndexConfig
from .utils import now_iso


class WatchManager:
    def __init__(self, db: Database, indexer: Indexer) -> None:
        self.db = db
        self.indexer = indexer
        self._tasks: dict[str, asyncio.Task[None]] = {}

    def start(self, corpus_id: str, poll_interval_s: int = 20) -> None:
        if corpus_id in self._tasks and not self._tasks[corpus_id].done():
            return
        self.db.execute(
            """
            INSERT INTO index_watchers (corpus_id, status, poll_interval_s, last_checked_at, last_change_at, fingerprint, error_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(corpus_id) DO UPDATE SET
              status=excluded.status,
              poll_interval_s=excluded.poll_interval_s,
              error_json=NULL
            """,
            (corpus_id, "running", poll_interval_s, now_iso(), None, None, None),
        )
        task = asyncio.create_task(self._loop(corpus_id=corpus_id, poll_interval_s=poll_interval_s))
        self._tasks[corpus_id] = task

    def stop(self, corpus_id: str) -> None:
        task = self._tasks.get(corpus_id)
        if task is not None:
            task.cancel()
        self.db.execute(
            "INSERT INTO index_watchers (corpus_id, status, poll_interval_s) VALUES (?, ?, ?) ON CONFLICT(corpus_id) DO UPDATE SET status=excluded.status",
            (corpus_id, "stopped", 20),
        )

    def status(self, corpus_id: str) -> dict[str, Any] | None:
        row = self.db.fetchone(
            "SELECT corpus_id, status, poll_interval_s, last_checked_at, last_change_at, fingerprint, error_json FROM index_watchers WHERE corpus_id = ?",
            (corpus_id,),
        )
        if row is None:
            return None
        return {
            "corpus_id": str(row["corpus_id"]),
            "status": str(row["status"]),
            "poll_interval_s": int(row["poll_interval_s"]),
            "last_checked_at": row["last_checked_at"],
            "last_change_at": row["last_change_at"],
            "fingerprint": row["fingerprint"],
            "error": json.loads(str(row["error_json"] or "null")),
        }

    def list_status(self) -> list[dict[str, Any]]:
        rows = self.db.fetchall("SELECT corpus_id, status, poll_interval_s, last_checked_at, last_change_at, fingerprint, error_json FROM index_watchers ORDER BY corpus_id ASC")
        return [
            {
                "corpus_id": str(row["corpus_id"]),
                "status": str(row["status"]),
                "poll_interval_s": int(row["poll_interval_s"]),
                "last_checked_at": row["last_checked_at"],
                "last_change_at": row["last_change_at"],
                "fingerprint": row["fingerprint"],
                "error": json.loads(str(row["error_json"] or "null")),
            }
            for row in rows
        ]

    async def shutdown(self) -> None:
        task_items = list(self._tasks.items())
        for corpus_id, task in task_items:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            finally:
                self._tasks.pop(corpus_id, None)

    async def _loop(self, corpus_id: str, poll_interval_s: int) -> None:
        while True:
            try:
                fingerprint = self._fingerprint(corpus_id)
                row = self.db.fetchone("SELECT fingerprint FROM index_watchers WHERE corpus_id = ?", (corpus_id,))
                previous = str(row["fingerprint"]) if row and row["fingerprint"] is not None else None
                changed = previous is not None and previous != fingerprint

                self.db.execute(
                    "UPDATE index_watchers SET status = ?, last_checked_at = ?, fingerprint = ?, error_json = NULL WHERE corpus_id = ?",
                    ("running", now_iso(), fingerprint, corpus_id),
                )

                if changed:
                    job_id = self.indexer.create_job(corpus_id)
                    self.db.execute(
                        "UPDATE index_watchers SET last_change_at = ? WHERE corpus_id = ?",
                        (now_iso(), corpus_id),
                    )
                    await self.indexer.run_job(job_id)

                await asyncio.sleep(max(3, poll_interval_s))
            except asyncio.CancelledError:
                self.db.execute("UPDATE index_watchers SET status = ? WHERE corpus_id = ?", ("stopped", corpus_id))
                raise
            except Exception as exc:  # noqa: BLE001
                self.db.execute(
                    "UPDATE index_watchers SET status = ?, error_json = ?, last_checked_at = ? WHERE corpus_id = ?",
                    ("error", json.dumps({"message": str(exc)}), now_iso(), corpus_id),
                )
                await asyncio.sleep(max(5, poll_interval_s))

    def _fingerprint(self, corpus_id: str) -> str:
        corpus = self.db.fetchone("SELECT root_path, index_config_json FROM corpora WHERE id = ?", (corpus_id,))
        if corpus is None:
            return "missing-corpus"

        root = Path(str(corpus["root_path"]))
        config = IndexConfig.model_validate_json(str(corpus["index_config_json"]))
        paths = self.indexer._collect_paths(root, config)

        parts: list[str] = []
        for path in paths:
            rel = path.relative_to(root).as_posix()
            stat = path.stat()
            parts.append(f"{rel}:{int(stat.st_mtime)}:{stat.st_size}")

        digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
        return f"sha256:{digest}"
