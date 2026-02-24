from pathlib import Path
import time

from fastapi.testclient import TestClient

from rlm_lens.main import create_app


def test_health() -> None:
    app = create_app()
    with TestClient(app) as client:
        res = client.get("/api/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"


def test_create_corpus_and_run(tmp_path: Path) -> None:
    corpus_root = tmp_path / "sample"
    corpus_root.mkdir()
    (corpus_root / "retry_policy.py").write_text("def with_retries():\n    pass\n")
    (corpus_root / "api.py").write_text("from retry_policy import with_retries\n")

    app = create_app()
    with TestClient(app) as client:
        corpus_res = client.post(
            "/api/corpora",
            json={
                "name": "tmp",
                "path": str(corpus_root),
                "index_config": {
                    "include_globs": ["**/*.py"],
                    "exclude_globs": [],
                    "max_file_bytes": 100000,
                },
                "start_index": False,
            },
        )
        assert corpus_res.status_code == 200
        corpus_id = corpus_res.json()["corpus_id"]

        index_res = client.post("/api/index", json={"corpus_id": corpus_id})
        assert index_res.status_code == 200
        job_id = index_res.json()["index_job_id"]

        for _ in range(100):
            job = client.get(f"/api/index/{job_id}").json()
            if job["status"] in {"succeeded", "failed"}:
                break
        assert job["status"] == "succeeded"

        run_res = client.post(
            "/api/runs",
            json={
                "corpus_id": corpus_id,
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
        )
        assert run_res.status_code == 200
        run_id = run_res.json()["run_id"]

        for _ in range(100):
            run = client.get(f"/api/runs/{run_id}").json()
            if run["status"] in {"succeeded", "failed", "partial_budget_exceeded"}:
                break
        assert run["status"] in {"succeeded", "partial_budget_exceeded"}
        assert len(run["citations"]) >= 1


def test_create_run_uses_ephemeral_provider_key_header(tmp_path: Path) -> None:
    corpus_root = tmp_path / "sample_header"
    corpus_root.mkdir()
    (corpus_root / "app.py").write_text("def run():\n    return 'ok'\n")

    app = create_app()
    captured: dict[str, str | None] = {}
    with TestClient(app) as client:
        corpus_res = client.post(
            "/api/corpora",
            json={
                "name": "header",
                "path": str(corpus_root),
                "index_config": {
                    "include_globs": ["**/*.py"],
                    "exclude_globs": [],
                    "max_file_bytes": 100000,
                },
                "start_index": False,
            },
        )
        assert corpus_res.status_code == 200
        corpus_id = corpus_res.json()["corpus_id"]

        async def fake_run(run_id: str, provider_api_key: str | None = None) -> None:
            captured["run_id"] = run_id
            captured["provider_api_key"] = provider_api_key

        client.app.state.services.runner.run = fake_run  # type: ignore[method-assign]

        run_res = client.post(
            "/api/runs",
            headers={"X-RLM-LENS-PROVIDER-KEY": "sk-session-key"},
            json={
                "corpus_id": corpus_id,
                "messages": [{"role": "user", "content": "where retry policy"}],
                "runtime": {
                    "provider": "openrouter",
                    "model": "openai/gpt-4o-mini",
                    "environment": "docker",
                    "max_depth": 2,
                    "max_iterations": 2,
                    "budgets": {"max_wall_time_s": 30, "max_subcalls": 4},
                },
            },
        )
        assert run_res.status_code == 200
        run_id = run_res.json()["run_id"]

        for _ in range(40):
            if captured:
                break
            time.sleep(0.01)
        assert captured["run_id"] == run_id
        assert captured["provider_api_key"] == "sk-session-key"

        row = client.app.state.services.db.fetchone("SELECT runtime_config_json FROM runs WHERE id = ?", (run_id,))
        assert row is not None
        assert "provider_api_key" not in str(row["runtime_config_json"])
