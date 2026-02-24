from __future__ import annotations

from pathlib import Path
import json
import time
from typing import cast
from urllib import request as urllib_request


BASE = "http://127.0.0.1:8765"


def _post(path: str, payload: dict[str, object]) -> dict[str, object]:
    req = urllib_request.Request(
        BASE + path,
        method="POST",
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload).encode("utf-8"),
    )
    with urllib_request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return cast(dict[str, object], data)


def _get(path: str) -> dict[str, object]:
    with urllib_request.urlopen(BASE + path, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return cast(dict[str, object], data)


def run_demo() -> None:
    root = Path.cwd().parent / "examples" / "sample_corpus"
    corpus = _post(
        "/api/corpora",
        {
            "name": "Sample Corpus",
            "path": str(root),
            "index_config": {
                "include_globs": ["**/*.md", "**/*.py", "**/*.sql"],
                "exclude_globs": ["**/.git/**"],
                "max_file_bytes": 1_000_000,
            },
            "start_index": True,
        },
    )
    job_id = str(corpus["index_job_id"])
    print(f"Created corpus {corpus['corpus_id']} and job {job_id}")

    for _ in range(120):
        job = _get(f"/api/index/{job_id}")
        if job["status"] in {"succeeded", "failed"}:
            break
        time.sleep(0.25)
    print("Index status:", job["status"])

    run = _post(
        "/api/runs",
        {
            "corpus_id": corpus["corpus_id"],
            "messages": [{"role": "user", "content": "Where is the retry policy defined?"}],
            "runtime": {
                "provider": "openai",
                "model": "gpt-5-nano",
                "environment": "docker",
                "max_depth": 2,
                "max_iterations": 4,
                "budgets": {"max_wall_time_s": 90, "max_subcalls": 40},
            },
        },
    )
    run_id = str(run["run_id"])
    print("Started run:", run_id)

    for _ in range(120):
        detail = _get(f"/api/runs/{run_id}")
        if detail["status"] in {"succeeded", "failed", "partial_budget_exceeded"}:
            citations = detail.get("citations")
            citations_count = len(citations) if isinstance(citations, list) else 0
            print("Run status:", detail["status"])
            print("Answer:\n", detail.get("final_answer", ""))
            print("Citations:", citations_count)
            break
        time.sleep(0.25)


if __name__ == "__main__":
    run_demo()
