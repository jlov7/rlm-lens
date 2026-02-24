from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import re
import sqlite3
from typing import Any

from .db import Database
from .utils import now_iso


VECTOR_DIMS = 64


@dataclass
class RetrievalHit:
    corpus_id: str
    path: str
    snippet: str
    start_line: int
    end_line: int
    bm25_score: float
    vector_score: float
    rerank_score: float
    combined_score: float


def text_vector(text: str, dims: int = VECTOR_DIMS) -> list[float]:
    vector = [0.0] * dims
    tokens = [token for token in re.findall(r"[a-z0-9_]+", text.lower()) if len(token) > 1]
    if not tokens:
        return vector
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:2], "big") % dims
        sign = 1.0 if digest[2] % 2 == 0 else -1.0
        vector[idx] += sign
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    if len(left) != len(right):
        size = min(len(left), len(right))
        left = left[:size]
        right = right[:size]
    dot = sum(a * b for a, b in zip(left, right, strict=False))
    return max(-1.0, min(1.0, dot))


class HybridRetriever:
    def __init__(self, db: Database) -> None:
        self.db = db

    def upsert_vector(self, corpus_id: str, path: str, text: str) -> None:
        vector = text_vector(text)
        self.db.execute(
            """
            INSERT INTO file_vectors (corpus_id, path, vector_json, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(corpus_id, path) DO UPDATE SET
              vector_json=excluded.vector_json,
              updated_at=excluded.updated_at
            """,
            (corpus_id, path, json.dumps(vector), now_iso()),
        )

    def delete_vector(self, corpus_id: str, path: str) -> None:
        self.db.execute("DELETE FROM file_vectors WHERE corpus_id = ? AND path = ?", (corpus_id, path))

    def search(
        self,
        corpus_ids: list[str],
        query: str,
        limit: int = 10,
        bm25_weight: float = 0.55,
        vector_weight: float = 0.35,
        rerank_weight: float = 0.10,
        corpus_weights: dict[str, float] | None = None,
    ) -> list[RetrievalHit]:
        query_text = query.strip() or "*"
        query_vector = text_vector(query)
        query_tokens = self._query_tokens(query)
        weights = corpus_weights or {}

        by_key: dict[tuple[str, str], RetrievalHit] = {}
        per_corpus_limit = max(limit * 6, 20)

        for corpus_id in corpus_ids:
            rows = self._fts_candidates(corpus_id=corpus_id, query=query_text, limit=per_corpus_limit)
            if not rows:
                rows = self._fallback_candidates(corpus_id=corpus_id, limit=per_corpus_limit)

            corpus_weight = max(0.0, float(weights.get(corpus_id, 1.0)))
            for row in rows:
                path = str(row["path"])
                content = str(row["content"])
                snippet = str(row["snippet"]) if row["snippet"] is not None else content[:240]
                rank_value = row["rank"]
                bm25_score = self._bm25_score(rank_value)

                vector = self._fetch_vector(corpus_id=corpus_id, path=path)
                if vector is None:
                    vector = text_vector(content)
                vector_score = max(0.0, cosine_similarity(query_vector, vector))

                rerank_score = self._rerank_score(content=content, query_tokens=query_tokens)
                combined = corpus_weight * ((bm25_weight * bm25_score) + (vector_weight * vector_score) + (rerank_weight * rerank_score))

                start_line, end_line = self._best_line_span(content.splitlines(), query_tokens)
                candidate = RetrievalHit(
                    corpus_id=corpus_id,
                    path=path,
                    snippet=snippet,
                    start_line=start_line,
                    end_line=end_line,
                    bm25_score=round(bm25_score, 4),
                    vector_score=round(vector_score, 4),
                    rerank_score=round(rerank_score, 4),
                    combined_score=round(combined, 4),
                )

                key = (corpus_id, path)
                existing = by_key.get(key)
                if existing is None or candidate.combined_score > existing.combined_score:
                    by_key[key] = candidate

        ranked = sorted(by_key.values(), key=lambda hit: hit.combined_score, reverse=True)
        return ranked[:limit]

    def _fetch_vector(self, corpus_id: str, path: str) -> list[float] | None:
        row = self.db.fetchone(
            "SELECT vector_json FROM file_vectors WHERE corpus_id = ? AND path = ?",
            (corpus_id, path),
        )
        if row is None:
            return None
        try:
            parsed = json.loads(str(row["vector_json"]))
        except json.JSONDecodeError:
            return None
        if not isinstance(parsed, list):
            return None
        return [float(value) for value in parsed]

    def _fts_candidates(self, corpus_id: str, query: str, limit: int) -> list[dict[str, Any]]:
        try:
            rows = self.db.fetchall(
                """
                SELECT f.path AS path,
                       snippet(file_fts, 2, '', '', ' ... ', 18) AS snippet,
                       bm25(file_fts) AS rank,
                       f.content AS content
                FROM file_fts AS f
                WHERE f.corpus_id = ? AND file_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (corpus_id, query, limit),
            )
        except sqlite3.OperationalError:
            return []

        return [
            {
                "path": row["path"],
                "snippet": row["snippet"],
                "rank": row["rank"],
                "content": row["content"],
            }
            for row in rows
        ]

    def _fallback_candidates(self, corpus_id: str, limit: int) -> list[dict[str, Any]]:
        rows = self.db.fetchall(
            "SELECT path, content FROM file_fts WHERE corpus_id = ? LIMIT ?",
            (corpus_id, limit),
        )
        return [{"path": row["path"], "snippet": str(row["content"])[:240], "rank": None, "content": row["content"]} for row in rows]

    def _bm25_score(self, rank_value: Any) -> float:
        if rank_value is None:
            return 0.1
        try:
            rank = float(rank_value)
        except (TypeError, ValueError):
            return 0.1
        return 1.0 / (1.0 + abs(rank))

    def _query_tokens(self, query: str) -> list[str]:
        stop_words = {
            "the",
            "a",
            "an",
            "is",
            "are",
            "where",
            "what",
            "how",
            "to",
            "of",
            "in",
            "for",
            "and",
            "or",
        }
        raw_tokens = [re.sub(r"[^a-z0-9_]", "", token.lower()) for token in query.split()]
        return [token for token in raw_tokens if token and token not in stop_words]

    def _rerank_score(self, content: str, query_tokens: list[str]) -> float:
        if not query_tokens:
            return 0.0
        lowered = content.lower()
        matched = sum(1 for token in query_tokens if token in lowered)
        return matched / len(query_tokens)

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
