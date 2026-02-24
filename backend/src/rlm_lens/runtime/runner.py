from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import time
from typing import Any

from ..db import Database
from ..events import EventBroker
from ..ids import make_id
from ..indexer import CorpusReader
from ..security import sha256_text
from ..utils import now_iso
from .adapter import RLMAdapter
from .grounding import grounding_report
from .logger import LensLogger


@dataclass
class RuntimeResult:
    status: str
    answer: str
    citations: list[dict[str, Any]]
    usage: dict[str, Any]


class RuntimeRunner:
    def __init__(self, db: Database, broker: EventBroker, data_dir: Path) -> None:
        self.db = db
        self.broker = broker
        self.data_dir = data_dir
        self.reader = CorpusReader(db)

    async def run(self, run_id: str) -> None:
        run = self.db.fetchone("SELECT id, corpus_id, runtime_config_json FROM runs WHERE id = ?", (run_id,))
        if run is None:
            return

        run_dir = self.data_dir / "runs" / run_id
        logger = LensLogger(run_id=run_id, run_dir=run_dir, db=self.db, broker=self.broker)
        runtime_config = json.loads(str(run["runtime_config_json"]))
        provider = str(runtime_config.get("provider", "openai"))
        environment = str(runtime_config.get("environment", "docker"))
        model = str(runtime_config.get("model", "gpt-5-nano"))
        adapter = RLMAdapter(model=model, provider=provider, environment=environment)

        self.db.execute("UPDATE runs SET status = ?, started_at = ? WHERE id = ?", ("running", now_iso(), run_id))
        await logger.log_status("running")

        messages = self.db.fetchall("SELECT role, content FROM messages WHERE run_id = ? ORDER BY id ASC", (run_id,))
        user_message = ""
        for message in reversed(messages):
            if str(message["role"]) == "user":
                user_message = str(message["content"])
                break

        corpus_id = str(run["corpus_id"])
        start = time.perf_counter()
        max_wall_time_s = int(runtime_config.get("budgets", {}).get("max_wall_time_s", 90))
        max_iterations = int(runtime_config.get("max_iterations", 10))
        max_subcalls = int(runtime_config.get("budgets", {}).get("max_subcalls", 40))
        performance_mode = bool(runtime_config.get("performance_mode", False))
        if performance_mode:
            max_iterations = min(max_iterations, 4)

        configured_targets = runtime_config.get("target_corpora", [])
        target_corpora = [str(item) for item in configured_targets if isinstance(item, str)]
        corpus_ids: list[str] = [corpus_id]
        for target in target_corpora:
            if target not in corpus_ids:
                corpus_ids.append(target)

        retrieval_config = runtime_config.get("retrieval", {})
        if not isinstance(retrieval_config, dict):
            retrieval_config = {}
        bm25_weight = float(retrieval_config.get("bm25_weight", 0.55))
        vector_weight = float(retrieval_config.get("vector_weight", 0.35))
        rerank_weight = float(retrieval_config.get("rerank_weight", 0.10))
        top_k = max(1, int(retrieval_config.get("top_k", 6)))
        corpus_weights = runtime_config.get("corpus_weights", {})
        corpus_weight_map = {str(key): float(value) for key, value in corpus_weights.items()} if isinstance(corpus_weights, dict) else {}

        metadata = {
            "root_model": model,
            "max_depth": int(runtime_config.get("max_depth", 2)),
            "max_iterations": max_iterations,
            "backend": provider,
            "backend_kwargs": {"model_name": model},
            "environment_type": environment,
            "environment_kwargs": {"fallback": "local"},
            "other_backends": None,
        }
        await logger.log_metadata(metadata)

        citations: list[dict[str, Any]] = []
        retrieval_steps: list[dict[str, Any]] = []
        usage_input = 0
        usage_output = 0
        total_subcalls = 0

        status = "succeeded"
        answer = ""

        try:
            for iteration in range(1, max_iterations + 1):
                elapsed = time.perf_counter() - start
                if elapsed >= max_wall_time_s or total_subcalls >= max_subcalls:
                    status = "partial_budget_exceeded"
                    await logger.log_budget(
                        {
                            "iteration": iteration,
                            "elapsed_s": round(elapsed, 3),
                            "max_wall_time_s": max_wall_time_s,
                            "total_subcalls": total_subcalls,
                            "max_subcalls": max_subcalls,
                        }
                    )
                    break

                hits = self.reader.search_hybrid(
                    corpus_ids=corpus_ids,
                    query=user_message,
                    limit=top_k,
                    bm25_weight=bm25_weight,
                    vector_weight=vector_weight,
                    rerank_weight=rerank_weight,
                    corpus_weights=corpus_weight_map,
                )
                retrieval_steps.append(
                    {
                        "iteration": iteration,
                        "candidate_count": len(hits),
                        "top_hits": [
                            {
                                "corpus_id": hit.corpus_id,
                                "path": hit.path,
                                "combined_score": hit.combined_score,
                                "bm25_score": hit.bm25_score,
                                "vector_score": hit.vector_score,
                                "rerank_score": hit.rerank_score,
                            }
                            for hit in hits[:5]
                        ],
                    }
                )
                top_paths = [f"{hit.corpus_id}:{hit.path}" for hit in hits[:3]]
                prompt = f"Answer the user query using corpus evidence. Query: {user_message}. Top files: {', '.join(top_paths)}"
                subcall = adapter.call_submodel(prompt)
                usage_input += subcall.total_input_tokens
                usage_output += subcall.total_output_tokens
                total_subcalls += 1

                code_blocks: list[dict[str, Any]] = []
                for hit in hits[:3]:
                    slice_data = self.reader.read_slice(hit.corpus_id, hit.path, hit.start_line, hit.end_line)
                    snippet = str(slice_data["text"])
                    if not snippet.strip():
                        continue
                    citation = {
                        "citation_id": make_id("cit"),
                        "corpus_id": hit.corpus_id,
                        "path": hit.path,
                        "start_line": int(slice_data["start_line"]),
                        "end_line": int(slice_data["end_line"]),
                        "snippet": snippet,
                        "content_hash": sha256_text(snippet),
                    }
                    citations.append(citation)

                    code_blocks.append(
                        {
                            "code": f"lens.read('{hit.corpus_id}:{hit.path}', {hit.start_line}, {hit.end_line})",
                            "result": {
                                "stdout": "",
                                "stderr": "",
                                "locals": {"path": hit.path, "corpus_id": hit.corpus_id},
                                "execution_time": 0.02,
                                "rlm_calls": [
                                    {
                                        "root_model": model,
                                        "prompt": subcall.prompt,
                                        "response": subcall.response,
                                        "usage_summary": {
                                            "model_usage_summaries": {
                                                model: {
                                                    "total_calls": 1,
                                                    "total_input_tokens": subcall.total_input_tokens,
                                                    "total_output_tokens": subcall.total_output_tokens,
                                                    "total_cost": subcall.total_cost,
                                                }
                                            },
                                            "total_cost": subcall.total_cost,
                                        },
                                        "execution_time": subcall.execution_time,
                                        "warnings": subcall.warnings,
                                    }
                                ],
                                "final_answer": None,
                            },
                        }
                    )

                citations = self._dedupe_citations(citations)
                answer = self._compose_answer(user_message=user_message, citations=citations)
                iteration_payload = {
                    "iteration": iteration,
                    "prompt": prompt,
                    "response": subcall.response,
                    "retrieval": retrieval_steps[-1],
                    "code_blocks": code_blocks,
                    "final_answer": answer,
                    "iteration_time": round(time.perf_counter() - start, 3),
                }
                await logger.log_iteration(iteration_payload)
                if iteration >= 2:
                    break

            if status == "partial_budget_exceeded":
                citations = self._dedupe_citations(citations)
                answer = self._compose_answer(
                    user_message=user_message,
                    citations=citations,
                    prefix="Partial result due to budget limits. Increase wall time or narrow query.",
                )

            usage = {
                "model_usage_summaries": {
                    model: {
                        "total_calls": total_subcalls,
                        "total_input_tokens": usage_input,
                        "total_output_tokens": usage_output,
                        "total_cost": 0.0,
                    }
                },
                "total_cost": 0.0,
                "wall_time_s": round(time.perf_counter() - start, 3),
                "total_subcalls": total_subcalls,
                "citations": len(citations),
                "warnings": adapter.warnings(),
                "performance_mode": performance_mode,
                "retrieval": {
                    "bm25_weight": bm25_weight,
                    "vector_weight": vector_weight,
                    "rerank_weight": rerank_weight,
                    "top_k": top_k,
                    "target_corpora": corpus_ids,
                    "steps": retrieval_steps,
                },
            }
            usage["grounding"] = grounding_report(answer=answer, citations=citations)

            self.db.execute(
                "UPDATE runs SET status = ?, finished_at = ?, final_answer_md = ?, usage_json = ? WHERE id = ?",
                (status, now_iso(), answer, json.dumps(usage), run_id),
            )
            self.db.execute("DELETE FROM citations WHERE run_id = ?", (run_id,))
            rows = [
                (
                    cit["citation_id"],
                    run_id,
                    cit.get("corpus_id"),
                    cit["path"],
                    cit["start_line"],
                    cit["end_line"],
                    cit["snippet"],
                    cit["content_hash"],
                )
                for cit in citations
            ]
            if rows:
                self.db.executemany(
                    "INSERT INTO citations (id, run_id, corpus_id, path, start_line, end_line, snippet, content_hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    rows,
                )

            await logger.complete({"status": status, "final_answer": answer, "usage": usage})
        except Exception as exc:  # noqa: BLE001
            self.db.execute(
                "UPDATE runs SET status = ?, finished_at = ?, error_json = ? WHERE id = ?",
                ("failed", now_iso(), json.dumps({"message": str(exc)}), run_id),
            )
            await logger.log_error(str(exc))
            await logger.complete({"status": "failed"})

    def _compose_answer(self, user_message: str, citations: list[dict[str, Any]], prefix: str | None = None) -> str:
        header = "## Summary\n"
        if prefix:
            header += f"{prefix}\n\n"
        header += f"Question: {user_message}\n\n"
        details = "## Evidence-backed details\n"
        if not citations:
            details += "- No evidence found in index.\n"
            return header + details

        bullets: list[str] = []
        for idx, citation in enumerate(citations[:5], start=1):
            corpus_prefix = f"{citation.get('corpus_id')}::" if citation.get("corpus_id") else ""
            bullets.append(f"- Evidence {idx}: `{corpus_prefix}{citation['path']}:L{citation['start_line']}-L{citation['end_line']}` supports the answer.")

        next_steps = "\n## What to check next\n- Re-run with a narrower scope if you need deeper line-level analysis.\n"
        return header + details + "\n".join(bullets) + next_steps

    def _dedupe_citations(self, citations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[tuple[str, str, int, int]] = set()
        result: list[dict[str, Any]] = []
        for citation in citations:
            key = (
                str(citation.get("corpus_id") or ""),
                str(citation["path"]),
                int(citation["start_line"]),
                int(citation["end_line"]),
            )
            if key in seen:
                continue
            seen.add(key)
            result.append(citation)
        return result
