from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from .db import Database
from .ids import make_id
from .utils import now_iso


@dataclass(frozen=True)
class PolicyPattern:
    category: str
    severity: str
    pattern: re.Pattern[str]


DEFAULT_POLICY_PATTERNS: list[PolicyPattern] = [
    PolicyPattern("email", "medium", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    PolicyPattern("phone", "low", re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b")),
    PolicyPattern("ssn", "high", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    PolicyPattern("openai_key", "critical", re.compile(r"sk-[A-Za-z0-9]{16,}")),
    PolicyPattern("aws_access_key", "critical", re.compile(r"AKIA[0-9A-Z]{16}")),
    PolicyPattern("bearer_token", "high", re.compile(r"Bearer\s+[A-Za-z0-9\-_.=]{12,}")),
]


class PolicyEngine:
    def __init__(self, db: Database) -> None:
        self.db = db

    def scan_text(self, corpus_id: str, path: str, text: str) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        lines = text.splitlines()
        for idx, line in enumerate(lines, start=1):
            for pattern in DEFAULT_POLICY_PATTERNS:
                if pattern.pattern.search(line):
                    findings.append(
                        {
                            "id": make_id("pii"),
                            "corpus_id": corpus_id,
                            "path": path,
                            "line_no": idx,
                            "category": pattern.category,
                            "severity": pattern.severity,
                            "preview": self._sanitize_preview(line),
                            "found_at": now_iso(),
                        }
                    )
        return findings

    def replace_findings_for_file(self, corpus_id: str, path: str, findings: list[dict[str, Any]]) -> None:
        self.db.execute("DELETE FROM pii_findings WHERE corpus_id = ? AND path = ?", (corpus_id, path))
        rows = [
            (
                finding["id"],
                finding["corpus_id"],
                finding["path"],
                finding["line_no"],
                finding["category"],
                finding["severity"],
                finding["preview"],
                finding["found_at"],
            )
            for finding in findings
        ]
        if rows:
            self.db.executemany(
                "INSERT INTO pii_findings (id, corpus_id, path, line_no, category, severity, preview, found_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                rows,
            )

    def policy_summary(self, corpus_id: str) -> dict[str, Any]:
        rows = self.db.fetchall(
            "SELECT category, severity, COUNT(*) AS count FROM pii_findings WHERE corpus_id = ? GROUP BY category, severity ORDER BY count DESC",
            (corpus_id,),
        )
        return {
            "corpus_id": corpus_id,
            "totals": [
                {
                    "category": str(row["category"]),
                    "severity": str(row["severity"]),
                    "count": int(row["count"]),
                }
                for row in rows
            ],
            "total_findings": sum(int(row["count"]) for row in rows),
        }

    def list_findings(self, corpus_id: str, limit: int = 200) -> list[dict[str, Any]]:
        rows = self.db.fetchall(
            "SELECT id, path, line_no, category, severity, preview, found_at FROM pii_findings WHERE corpus_id = ? ORDER BY found_at DESC LIMIT ?",
            (corpus_id, limit),
        )
        return [
            {
                "id": str(row["id"]),
                "path": str(row["path"]),
                "line_no": int(row["line_no"]),
                "category": str(row["category"]),
                "severity": str(row["severity"]),
                "preview": str(row["preview"]),
                "found_at": str(row["found_at"]),
            }
            for row in rows
        ]

    def _sanitize_preview(self, line: str) -> str:
        collapsed = " ".join(line.strip().split())
        if len(collapsed) <= 180:
            return collapsed
        return f"{collapsed[:177]}..."
