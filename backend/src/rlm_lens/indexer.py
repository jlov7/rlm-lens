from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import fnmatch
import hashlib
import json
import os
import re
from typing import Any

from .db import Database
from .events import EventBroker
from .ids import make_id
from .models import IndexConfig
from .policy import PolicyEngine
from .retrieval import HybridRetriever
from .security import contains_hidden_segment, is_binary_bytes, is_denied, relative_path_within_root, sha256_bytes
from .utils import now_iso


@dataclass
class IndexSummary:
    files_total: int
    files_indexed: int
    files_unchanged: int
    files_deleted: int
    files_skipped: dict[str, int]
    snapshot_hash: str


class Indexer:
    def __init__(self, db: Database, broker: EventBroker) -> None:
        self.db = db
        self.broker = broker
        self.retriever = HybridRetriever(db)
        self.policy = PolicyEngine(db)

    def create_job(self, corpus_id: str) -> str:
        job_id = make_id("job")
        self.db.execute(
            "INSERT INTO index_jobs (id, corpus_id, status, progress_json) VALUES (?, ?, ?, ?)",
            (job_id, corpus_id, "queued", json.dumps({"files_total": 0, "files_done": 0, "current_path": None})),
        )
        self.db.execute(
            "UPDATE corpora SET last_index_job_id = ?, updated_at = ? WHERE id = ?",
            (job_id, now_iso(), corpus_id),
        )
        return job_id

    async def run_job(self, job_id: str) -> None:
        job = self.db.fetchone("SELECT id, corpus_id FROM index_jobs WHERE id = ?", (job_id,))
        if job is None:
            return
        corpus = self.db.fetchone("SELECT id, root_path, index_config_json FROM corpora WHERE id = ?", (str(job["corpus_id"]),))
        if corpus is None:
            return

        started_at = now_iso()
        self.db.execute(
            "UPDATE index_jobs SET status = ?, started_at = ? WHERE id = ?",
            ("running", started_at, job_id),
        )

        root = Path(str(corpus["root_path"]))
        config = IndexConfig.model_validate_json(str(corpus["index_config_json"]))
        skipped: dict[str, int] = {"binary": 0, "exclude": 0, "size": 0, "decode": 0, "denied": 0}

        try:
            file_paths = self._collect_paths(root, config)
            files_total = len(file_paths)
            files_done = 0
            files_indexed = 0
            files_unchanged = 0
            current_paths: set[str] = set()

            for absolute_path in file_paths:
                files_done += 1
                rel_path = relative_path_within_root(root, absolute_path)
                current_paths.add(rel_path)
                progress = {"files_total": files_total, "files_done": files_done, "current_path": rel_path}
                await self.broker.publish("index", job_id, {"type": "index.progress", **progress})
                self.db.execute(
                    "UPDATE index_jobs SET progress_json = ? WHERE id = ?",
                    (json.dumps(progress), job_id),
                )

                if is_denied(rel_path, config.exclude_globs):
                    skipped["denied"] += 1
                    continue

                size = absolute_path.stat().st_size
                if size > config.max_file_bytes:
                    skipped["size"] += 1
                    continue

                raw = absolute_path.read_bytes()
                if is_binary_bytes(raw):
                    skipped["binary"] += 1
                    continue

                try:
                    text = raw.decode("utf-8")
                except UnicodeDecodeError:
                    skipped["decode"] += 1
                    continue

                sha = sha256_bytes(raw)
                mtime = absolute_path.stat().st_mtime
                existing = self.db.fetchone(
                    "SELECT sha256, bytes, mtime FROM files WHERE corpus_id = ? AND path = ?",
                    (str(corpus["id"]), rel_path),
                )

                unchanged = existing is not None and str(existing["sha256"]) == sha and int(existing["bytes"]) == len(raw) and float(existing["mtime"]) == mtime
                if unchanged:
                    files_unchanged += 1
                    continue

                files_indexed += 1
                self.db.execute(
                    """
                    INSERT INTO files (corpus_id, path, sha256, bytes, mtime, is_binary, indexed_at, language_hint)
                    VALUES (?, ?, ?, ?, ?, 0, ?, ?)
                    ON CONFLICT(corpus_id, path) DO UPDATE SET
                      sha256=excluded.sha256,
                      bytes=excluded.bytes,
                      mtime=excluded.mtime,
                      indexed_at=excluded.indexed_at,
                      language_hint=excluded.language_hint
                    """,
                    (str(corpus["id"]), rel_path, sha, len(raw), mtime, now_iso(), self._language_hint(rel_path)),
                )
                self.db.execute("DELETE FROM file_fts WHERE corpus_id = ? AND path = ?", (str(corpus["id"]), rel_path))
                self.db.execute(
                    "INSERT INTO file_fts (corpus_id, path, content) VALUES (?, ?, ?)",
                    (str(corpus["id"]), rel_path, text),
                )
                self.retriever.upsert_vector(corpus_id=str(corpus["id"]), path=rel_path, text=text)
                findings = self.policy.scan_text(corpus_id=str(corpus["id"]), path=rel_path, text=text)
                self.policy.replace_findings_for_file(corpus_id=str(corpus["id"]), path=rel_path, findings=findings)

            files_deleted = 0
            existing_rows = self.db.fetchall("SELECT path FROM files WHERE corpus_id = ?", (str(corpus["id"]),))
            existing_paths = {str(row["path"]) for row in existing_rows}
            stale_paths = sorted(existing_paths - current_paths)
            for stale_path in stale_paths:
                files_deleted += 1
                self.db.execute("DELETE FROM files WHERE corpus_id = ? AND path = ?", (str(corpus["id"]), stale_path))
                self.db.execute("DELETE FROM file_fts WHERE corpus_id = ? AND path = ?", (str(corpus["id"]), stale_path))
                self.db.execute("DELETE FROM pii_findings WHERE corpus_id = ? AND path = ?", (str(corpus["id"]), stale_path))
                self.retriever.delete_vector(corpus_id=str(corpus["id"]), path=stale_path)

            snapshot_hash = self._snapshot_hash(str(corpus["id"]), root, config)
            summary = IndexSummary(
                files_total=files_total,
                files_indexed=files_indexed,
                files_unchanged=files_unchanged,
                files_deleted=files_deleted,
                files_skipped={k: v for k, v in skipped.items() if v > 0},
                snapshot_hash=snapshot_hash,
            )
            self.db.execute(
                "UPDATE index_jobs SET status = ?, finished_at = ?, summary_json = ?, progress_json = ? WHERE id = ?",
                (
                    "succeeded",
                    now_iso(),
                    json.dumps(summary.__dict__),
                    json.dumps({"files_total": files_total, "files_done": files_total, "current_path": None}),
                    job_id,
                ),
            )
            self.db.execute(
                "UPDATE corpora SET last_indexed_at = ?, updated_at = ?, last_snapshot_hash = ?, latest_index_summary_json = ? WHERE id = ?",
                (now_iso(), now_iso(), snapshot_hash, json.dumps(summary.__dict__), str(corpus["id"])),
            )
            await self.broker.publish("index", job_id, {"type": "index.complete", **summary.__dict__})
        except Exception as exc:  # noqa: BLE001
            error_payload = {"message": str(exc)}
            self.db.execute(
                "UPDATE index_jobs SET status = ?, finished_at = ?, error_json = ? WHERE id = ?",
                ("failed", now_iso(), json.dumps(error_payload), job_id),
            )
            await self.broker.publish("index", job_id, {"type": "index.error", **error_payload})
        finally:
            await self.broker.close_topic("index", job_id)

    def _collect_paths(self, root: Path, config: IndexConfig) -> list[Path]:
        if not root.exists():
            return []

        include_globs = config.include_globs or ["**/*"]
        results: list[Path] = []
        for current_root, _dirs, files in os.walk(root):
            for name in files:
                absolute_path = Path(current_root) / name
                rel_path = absolute_path.relative_to(root).as_posix()
                if contains_hidden_segment(rel_path):
                    continue
                if any(self._glob_match(rel_path, pattern) for pattern in config.exclude_globs):
                    continue
                if not any(self._glob_match(rel_path, pattern) for pattern in include_globs):
                    continue
                results.append(absolute_path)
        return sorted(results)

    def _glob_match(self, path: str, pattern: str) -> bool:
        if fnmatch.fnmatch(path, pattern):
            return True
        if pattern.startswith("**/"):
            return fnmatch.fnmatch(path, pattern[3:])
        return False

    def _snapshot_hash(self, corpus_id: str, root: Path, config: IndexConfig) -> str:
        files = self.db.fetchall(
            "SELECT path, sha256, bytes, mtime FROM files WHERE corpus_id = ? ORDER BY path ASC",
            (corpus_id,),
        )
        seed = {
            "root_path": str(root.resolve()),
            "config": config.model_dump(mode="json"),
            "files": [[str(row["path"]), str(row["sha256"]), int(row["bytes"]), float(row["mtime"])] for row in files],
        }
        digest = hashlib.sha256(json.dumps(seed, sort_keys=True).encode("utf-8")).hexdigest()
        return f"sha256:{digest}"

    def _language_hint(self, path: str) -> str | None:
        suffix = Path(path).suffix.lower()
        if suffix:
            return suffix.removeprefix(".")
        return None


@dataclass
class SearchHit:
    corpus_id: str
    path: str
    snippet: str
    start_line: int
    end_line: int
    bm25_score: float = 0.0
    vector_score: float = 0.0
    rerank_score: float = 0.0
    combined_score: float = 0.0


class CorpusReader:
    def __init__(self, db: Database) -> None:
        self.db = db
        self.hybrid = HybridRetriever(db)
        self._cache: dict[tuple[str, str, int, float, float, float], list[SearchHit]] = {}

    def search(self, corpus_id: str, query: str, limit: int = 10) -> list[SearchHit]:
        return self.search_hybrid(corpus_ids=[corpus_id], query=query, limit=limit)

    def search_hybrid(
        self,
        corpus_ids: list[str],
        query: str,
        limit: int = 10,
        bm25_weight: float = 0.55,
        vector_weight: float = 0.35,
        rerank_weight: float = 0.10,
        corpus_weights: dict[str, float] | None = None,
    ) -> list[SearchHit]:
        corpus_key = ",".join(sorted(corpus_ids))
        cache_key = (corpus_key, query.strip().lower(), limit, bm25_weight, vector_weight, rerank_weight)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return list(cached)

        retrieved = self.hybrid.search(
            corpus_ids=corpus_ids,
            query=query,
            limit=limit,
            bm25_weight=bm25_weight,
            vector_weight=vector_weight,
            rerank_weight=rerank_weight,
            corpus_weights=corpus_weights,
        )
        hits = [
            SearchHit(
                corpus_id=hit.corpus_id,
                path=hit.path,
                snippet=hit.snippet,
                start_line=hit.start_line,
                end_line=hit.end_line,
                bm25_score=hit.bm25_score,
                vector_score=hit.vector_score,
                rerank_score=hit.rerank_score,
                combined_score=hit.combined_score,
            )
            for hit in retrieved
        ]
        self._cache[cache_key] = list(hits)
        if len(self._cache) > 128:
            oldest = next(iter(self._cache))
            self._cache.pop(oldest, None)
        return hits

    def _query_tokens(self, query: str) -> list[str]:
        stop_words = {"the", "a", "an", "is", "are", "where", "what", "how", "to", "of", "in", "for", "and", "or"}
        raw_tokens = [re.sub(r"[^a-z0-9_]", "", token.lower()) for token in query.split()]
        return [token for token in raw_tokens if token and token not in stop_words]

    def _best_line_span(self, lines: list[str], tokens: list[str]) -> tuple[int, int]:
        if not lines:
            return (1, 1)
        if not tokens:
            first_non_empty = next((idx for idx, line in enumerate(lines, start=1) if line.strip()), 1)
            return (first_non_empty, min(first_non_empty + 4, len(lines)))

        best_index = 1
        best_score = -1
        for idx, line in enumerate(lines, start=1):
            lowered = line.lower()
            score = sum(lowered.count(token) for token in tokens)
            if score > best_score:
                best_score = score
                best_index = idx

        return (best_index, min(best_index + 5, len(lines)))

    def read_text(self, corpus_id: str, path: str) -> str:
        corpus = self.db.fetchone("SELECT root_path FROM corpora WHERE id = ?", (corpus_id,))
        if corpus is None:
            raise ValueError("Corpus not found")
        root = Path(str(corpus["root_path"]))
        full_path = (root / path).resolve()
        if root.resolve() not in full_path.parents and root.resolve() != full_path:
            raise ValueError("Path traversal is not allowed")
        if not full_path.is_file():
            raise ValueError("File not found")
        return full_path.read_text(encoding="utf-8", errors="ignore")

    def read_slice(self, corpus_id: str, path: str, start_line: int, end_line: int) -> dict[str, Any]:
        text = self.read_text(corpus_id, path)
        lines = text.splitlines()
        start = max(1, start_line)
        end = min(max(start, end_line), len(lines))
        sliced = "\n".join(lines[start - 1 : end])
        return {
            "path": path,
            "start_line": start,
            "end_line": end,
            "text": sliced,
            "content_hash": hashlib.sha256(sliced.encode("utf-8")).hexdigest(),
        }
