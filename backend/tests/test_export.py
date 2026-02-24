from pathlib import Path
import time
import zipfile

from fastapi.testclient import TestClient

from rlm_lens.main import create_app


def test_export_bundle_contains_required_files(tmp_path: Path) -> None:
    corpus_root = tmp_path / "corpus"
    corpus_root.mkdir()
    (corpus_root / "retry_policy.py").write_text("class RetryPolicy:\n    max_attempts = 5\n")
    (corpus_root / "api.py").write_text("from retry_policy import RetryPolicy\n")

    app = create_app()
    with TestClient(app) as client:
        corpus = client.post(
            "/api/corpora",
            json={
                "name": "export-tests",
                "path": str(corpus_root),
                "index_config": {
                    "include_globs": ["**/*.py"],
                    "exclude_globs": [],
                    "max_file_bytes": 100000,
                },
                "start_index": True,
            },
        ).json()

        job_id = corpus["index_job_id"]
        for _ in range(120):
            job = client.get(f"/api/index/{job_id}").json()
            if job["status"] in {"succeeded", "failed"}:
                break
            time.sleep(0.02)
        assert job["status"] == "succeeded"

        run_id = client.post(
            "/api/runs",
            json={
                "corpus_id": corpus["corpus_id"],
                "messages": [{"role": "user", "content": "where retry policy"}],
                "runtime": {
                    "provider": "openai",
                    "model": "gpt-5-nano",
                    "environment": "docker",
                    "max_depth": 2,
                    "max_iterations": 4,
                    "budgets": {"max_wall_time_s": 90, "max_subcalls": 40},
                },
            },
        ).json()["run_id"]

        for _ in range(240):
            run = client.get(f"/api/runs/{run_id}").json()
            if run["status"] in {"succeeded", "failed", "partial_budget_exceeded"}:
                break
            time.sleep(0.03)

        export = client.post(f"/api/runs/{run_id}/export").json()
        zip_path = Path(export["zip_path"])
        assert zip_path.exists()

        with zipfile.ZipFile(zip_path, "r") as archive:
            names = set(archive.namelist())
            assert "answer.md" in names
            assert "citations.json" in names
            assert "trace.jsonl" in names
            assert "run.json" in names
            assert "corpus_manifest.json" in names
            assert "viewer/index.html" in names
            assert "viewer/run-data.json" in names
