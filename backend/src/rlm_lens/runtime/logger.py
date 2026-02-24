from __future__ import annotations

from pathlib import Path
import json
from typing import Any

from ..db import Database
from ..events import EventBroker
from ..security import redact_secrets
from ..utils import now_iso


class LensLogger:
    def __init__(self, run_id: str, run_dir: Path, db: Database, broker: EventBroker) -> None:
        self.run_id = run_id
        self.run_dir = run_dir
        self.db = db
        self.broker = broker
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.trace_path = self.run_dir / "trace.jsonl"
        self._seq = 0

    async def log_metadata(self, payload: dict[str, Any]) -> None:
        event = {"type": "metadata", "timestamp": now_iso(), **payload}
        await self._persist(event)
        await self.broker.publish("run", self.run_id, {"type": "run.metadata", **event})

    async def log_iteration(self, payload: dict[str, Any]) -> None:
        event = {"type": "iteration", "timestamp": now_iso(), **payload}
        await self._persist(event)
        await self.broker.publish("run", self.run_id, {"type": "run.iteration", **event})
        for code_block in payload.get("code_blocks", []):
            await self.broker.publish(
                "run",
                self.run_id,
                {"type": "run.code_block", "timestamp": now_iso(), "iteration": payload.get("iteration"), **code_block},
            )
            for subcall in code_block.get("result", {}).get("rlm_calls", []):
                await self.broker.publish(
                    "run",
                    self.run_id,
                    {"type": "run.subcall", "timestamp": now_iso(), "iteration": payload.get("iteration"), **subcall},
                )

    async def log_status(self, status: str, payload: dict[str, Any] | None = None) -> None:
        event = {"type": "run.status", "timestamp": now_iso(), "status": status, "payload": payload or {}}
        await self.broker.publish("run", self.run_id, event)

    async def log_budget(self, payload: dict[str, Any]) -> None:
        await self.broker.publish("run", self.run_id, {"type": "run.budget", "timestamp": now_iso(), **payload})

    async def log_error(self, error: str) -> None:
        await self.broker.publish("run", self.run_id, {"type": "run.error", "timestamp": now_iso(), "error": error})

    async def complete(self, payload: dict[str, Any]) -> None:
        await self.broker.publish("run", self.run_id, {"type": "run.complete", "timestamp": now_iso(), **payload})
        await self.broker.close_topic("run", self.run_id)

    async def _persist(self, event: dict[str, Any]) -> None:
        sanitized = redact_secrets(json.dumps(event, ensure_ascii=False))
        with self.trace_path.open("a", encoding="utf-8") as handle:
            handle.write(sanitized)
            handle.write("\n")

        self._seq += 1
        self.db.execute(
            "INSERT INTO trace_events (run_id, seq, ts, type, payload_json) VALUES (?, ?, ?, ?, ?)",
            (self.run_id, self._seq, now_iso(), str(event["type"]), sanitized),
        )
