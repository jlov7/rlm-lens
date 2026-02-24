from __future__ import annotations

import json
from typing import Any

from .db import Database
from .ids import make_id
from .runtime.runner import RuntimeRunner
from .utils import now_iso


DEFAULT_EVAL_QUERIES = [
    "Summarize the architecture and cite the most important files.",
    "Where is retry behavior defined? Cite exact lines.",
    "Find where the database schema is referenced and cite lines.",
]


class EvaluationEngine:
    def __init__(self, db: Database, runner: RuntimeRunner) -> None:
        self.db = db
        self.runner = runner

    def create_eval(self, config: dict[str, Any]) -> str:
        eval_id = make_id("eval")
        self.db.execute(
            "INSERT INTO eval_runs (id, status, created_at, config_json) VALUES (?, ?, ?, ?)",
            (eval_id, "queued", now_iso(), json.dumps(config)),
        )
        return eval_id

    async def run_eval(self, eval_id: str) -> None:
        row = self.db.fetchone("SELECT config_json FROM eval_runs WHERE id = ?", (eval_id,))
        if row is None:
            return

        config = json.loads(str(row["config_json"]))
        corpus_id = str(config.get("corpus_id", ""))
        runtime = dict(config.get("runtime", {}))
        queries = list(config.get("queries") or DEFAULT_EVAL_QUERIES)
        runtime.setdefault("provider", "openai")
        runtime.setdefault("model", "gpt-5-nano")
        runtime.setdefault("environment", "docker")
        runtime.setdefault("max_depth", 2)
        runtime.setdefault("max_iterations", 6)
        runtime.setdefault("budgets", {"max_wall_time_s": 90, "max_subcalls": 40})

        self.db.execute(
            "UPDATE eval_runs SET status = ?, started_at = ?, error_json = NULL WHERE id = ?",
            ("running", now_iso(), eval_id),
        )

        results: list[dict[str, Any]] = []
        try:
            for query in queries:
                run_id = make_id("run")
                snapshot_hash = self.db.fetch_value("SELECT last_snapshot_hash FROM corpora WHERE id = ?", (corpus_id,))
                self.db.execute(
                    "INSERT INTO runs (id, corpus_id, snapshot_hash, status, created_at, runtime_config_json) VALUES (?, ?, ?, ?, ?, ?)",
                    (run_id, corpus_id, str(snapshot_hash or ""), "running", now_iso(), json.dumps(runtime)),
                )
                self.db.execute(
                    "INSERT INTO messages (run_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                    (run_id, "user", query, now_iso()),
                )
                await self.runner.run(run_id)

                run = self.db.fetchone("SELECT status, usage_json, final_answer_md FROM runs WHERE id = ?", (run_id,))
                citations_count = int(self.db.fetch_value("SELECT COUNT(*) FROM citations WHERE run_id = ?", (run_id,)) or 0)
                usage = json.loads(str(run["usage_json"] or "{}")) if run else {}
                results.append(
                    {
                        "run_id": run_id,
                        "query": query,
                        "status": str(run["status"]) if run else "failed",
                        "citations": citations_count,
                        "grounding_score": usage.get("grounding", {}).get("grounding_score"),
                        "wall_time_s": usage.get("wall_time_s"),
                        "answer_preview": str((run["final_answer_md"] or "")[:180]) if run else "",
                    }
                )

            summary = self._summarize(results)
            self.db.execute(
                "UPDATE eval_runs SET status = ?, finished_at = ?, summary_json = ?, details_json = ? WHERE id = ?",
                ("succeeded", now_iso(), json.dumps(summary), json.dumps({"runs": results}), eval_id),
            )
        except Exception as exc:  # noqa: BLE001
            self.db.execute(
                "UPDATE eval_runs SET status = ?, finished_at = ?, error_json = ? WHERE id = ?",
                ("failed", now_iso(), json.dumps({"message": str(exc)}), eval_id),
            )

    def get_eval(self, eval_id: str) -> dict[str, Any] | None:
        row = self.db.fetchone(
            "SELECT id, status, created_at, started_at, finished_at, config_json, summary_json, details_json, error_json FROM eval_runs WHERE id = ?",
            (eval_id,),
        )
        if row is None:
            return None
        return {
            "eval_id": str(row["id"]),
            "status": str(row["status"]),
            "created_at": str(row["created_at"]),
            "started_at": row["started_at"],
            "finished_at": row["finished_at"],
            "config": json.loads(str(row["config_json"])),
            "summary": json.loads(str(row["summary_json"] or "{}")),
            "details": json.loads(str(row["details_json"] or "{}")),
            "error": json.loads(str(row["error_json"] or "null")),
        }

    def list_evals(self, limit: int = 20) -> list[dict[str, Any]]:
        rows = self.db.fetchall(
            "SELECT id, status, created_at, started_at, finished_at, summary_json FROM eval_runs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        return [
            {
                "eval_id": str(row["id"]),
                "status": str(row["status"]),
                "created_at": str(row["created_at"]),
                "started_at": row["started_at"],
                "finished_at": row["finished_at"],
                "summary": json.loads(str(row["summary_json"] or "{}")),
            }
            for row in rows
        ]

    def _summarize(self, runs: list[dict[str, Any]]) -> dict[str, Any]:
        if not runs:
            return {
                "total_runs": 0,
                "success_rate": 0.0,
                "avg_grounding": 0.0,
                "avg_citations": 0.0,
                "avg_wall_time_s": 0.0,
            }

        total = len(runs)
        succeeded = sum(1 for run in runs if run["status"] in {"succeeded", "partial_budget_exceeded"})
        grounding_values = [float(run["grounding_score"]) for run in runs if isinstance(run.get("grounding_score"), (int, float))]
        citations_values = [int(run["citations"]) for run in runs]
        wall_values = [float(run["wall_time_s"]) for run in runs if isinstance(run.get("wall_time_s"), (int, float))]

        return {
            "total_runs": total,
            "success_rate": round(succeeded / total, 3),
            "avg_grounding": round(sum(grounding_values) / max(1, len(grounding_values)), 3),
            "avg_citations": round(sum(citations_values) / total, 3),
            "avg_wall_time_s": round(sum(wall_values) / max(1, len(wall_values)), 3),
        }
