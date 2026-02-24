from __future__ import annotations

from pathlib import Path
import json
import zipfile
from typing import Any

from .db import Database
from .ids import make_id
from .utils import now_iso


class Exporter:
    def __init__(self, db: Database, data_dir: Path) -> None:
        self.db = db
        self.data_dir = data_dir

    def export_run(self, run_id: str) -> dict[str, Any]:
        run = self.db.fetchone(
            "SELECT id, corpus_id, status, runtime_config_json, final_answer_md, usage_json, created_at, started_at, finished_at FROM runs WHERE id = ?",
            (run_id,),
        )
        if run is None:
            raise ValueError("Run not found")

        citations_rows = self.db.fetchall(
            "SELECT id, corpus_id, path, start_line, end_line, snippet, content_hash FROM citations WHERE run_id = ? ORDER BY rowid ASC",
            (run_id,),
        )
        citations = [
            {
                "citation_id": str(row["id"]),
                "corpus_id": row["corpus_id"],
                "path": str(row["path"]),
                "start_line": int(row["start_line"]),
                "end_line": int(row["end_line"]),
                "snippet": str(row["snippet"]),
                "content_hash": str(row["content_hash"]),
            }
            for row in citations_rows
        ]

        corpus = self.db.fetchone("SELECT root_path, index_config_json, last_snapshot_hash FROM corpora WHERE id = ?", (str(run["corpus_id"]),))
        files = self.db.fetchall(
            "SELECT path, sha256, bytes, mtime FROM files WHERE corpus_id = ? ORDER BY path ASC",
            (str(run["corpus_id"]),),
        )

        run_payload = {
            "run_id": str(run["id"]),
            "corpus_id": str(run["corpus_id"]),
            "status": str(run["status"]),
            "runtime_config": json.loads(str(run["runtime_config_json"])),
            "usage": json.loads(str(run["usage_json"] or "{}")),
            "created_at": str(run["created_at"]),
            "started_at": str(run["started_at"]),
            "finished_at": str(run["finished_at"]),
        }
        manifest = {
            "corpus_id": str(run["corpus_id"]),
            "root_path": str(corpus["root_path"]) if corpus else "",
            "snapshot_hash": str(corpus["last_snapshot_hash"]) if corpus else None,
            "index_config": json.loads(str(corpus["index_config_json"])) if corpus else {},
            "files": [
                {
                    "path": str(row["path"]),
                    "sha256": str(row["sha256"]),
                    "bytes": int(row["bytes"]),
                    "mtime": float(row["mtime"]),
                }
                for row in files
            ],
        }

        exports_dir = self.data_dir / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)
        export_id = make_id("exp")
        zip_path = exports_dir / f"{run_id}_{now_iso().replace(':', '-')}.zip"

        run_dir = self.data_dir / "runs" / run_id
        trace_path = run_dir / "trace.jsonl"

        viewer_payload = {
            "run": run_payload,
            "answer": str(run["final_answer_md"] or ""),
            "citations": citations,
            "manifest": manifest,
        }

        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("answer.md", str(run["final_answer_md"] or ""))
            zf.writestr("citations.json", json.dumps(citations, indent=2))
            zf.writestr("run.json", json.dumps(run_payload, indent=2))
            zf.writestr("corpus_manifest.json", json.dumps(manifest, indent=2))
            zf.writestr("viewer/run-data.json", json.dumps(viewer_payload, indent=2))
            zf.writestr("viewer/index.html", self.render_share_view_html(viewer_payload))
            if trace_path.exists():
                zf.write(trace_path, arcname="trace.jsonl")
            else:
                zf.writestr("trace.jsonl", "")

        self.db.execute(
            "INSERT INTO exports (id, run_id, created_at, zip_path, manifest_json) VALUES (?, ?, ?, ?, ?)",
            (
                export_id,
                run_id,
                now_iso(),
                str(zip_path),
                json.dumps(
                    {
                        "files": [
                            "answer.md",
                            "citations.json",
                            "run.json",
                            "corpus_manifest.json",
                            "trace.jsonl",
                            "viewer/index.html",
                            "viewer/run-data.json",
                        ]
                    }
                ),
            ),
        )
        return {"export_id": export_id, "zip_path": str(zip_path)}

    def render_share_view_html(self, payload: dict[str, Any]) -> str:
        answer = str(payload.get("answer", ""))
        run = payload.get("run", {})
        citations = payload.get("citations", [])
        answer_html = answer.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>RLM-Lens Share View</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 24px; background:#08141f; color:#dff8ff; }}
    .card {{ border:1px solid #2f4d5f; border-radius:12px; padding:16px; margin-bottom:14px; background:#0f1e2b; }}
    h1,h2 {{ margin:0 0 8px; }}
    pre {{ white-space:pre-wrap; background:#0a1722; border:1px solid #294254; padding:12px; border-radius:8px; }}
    .pill {{ display:inline-block; margin-right:6px; margin-bottom:6px; padding:4px 10px; border:1px solid #375e73; border-radius:999px; color:#9cefff; font-size:12px; }}
    code {{ color:#93c8ff; }}
  </style>
</head>
<body>
  <h1>RLM-Lens Share View</h1>
  <div class="card">
    <h2>Run</h2>
    <div class="pill">Run {run.get("run_id", "")}</div>
    <div class="pill">Status {run.get("status", "")}</div>
    <div class="pill">Corpus {run.get("corpus_id", "")}</div>
  </div>
  <div class="card">
    <h2>Answer</h2>
    <pre>{answer_html}</pre>
  </div>
  <div class="card">
    <h2>Citations ({len(citations)})</h2>
    <pre>{json.dumps(citations, indent=2)}</pre>
  </div>
</body>
</html>
"""
