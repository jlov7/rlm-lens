from __future__ import annotations

from pathlib import Path
import time

from fastapi.testclient import TestClient

from rlm_lens.main import create_app


def _create_corpus(client: TestClient, corpus_root: Path) -> str:
    response = client.post(
        "/api/corpora",
        json={
            "name": "advanced-api",
            "path": str(corpus_root),
            "index_config": {
                "include_globs": ["**/*.py", "**/*.md", "**/*.sql", "**/*.txt"],
                "exclude_globs": [],
                "max_file_bytes": 1_000_000,
            },
            "start_index": False,
        },
    )
    assert response.status_code == 200
    return str(response.json()["corpus_id"])


def _start_index(client: TestClient, corpus_id: str) -> str:
    response = client.post("/api/index", json={"corpus_id": corpus_id})
    assert response.status_code == 200
    return str(response.json()["index_job_id"])


def _wait_for_index(client: TestClient, job_id: str) -> dict[str, object]:
    for _ in range(160):
        job = client.get(f"/api/index/{job_id}").json()
        if job["status"] in {"succeeded", "failed"}:
            return job
        time.sleep(0.02)
    raise AssertionError("Index job did not complete in time")


def _start_run(client: TestClient, corpus_id: str, question: str) -> str:
    response = client.post(
        "/api/runs",
        json={
            "corpus_id": corpus_id,
            "messages": [{"role": "user", "content": question}],
            "runtime": {
                "provider": "openai",
                "model": "gpt-5-nano",
                "environment": "docker",
                "max_depth": 2,
                "max_iterations": 4,
                "budgets": {"max_wall_time_s": 90, "max_subcalls": 40},
                "retrieval": {"bm25_weight": 0.5, "vector_weight": 0.4, "rerank_weight": 0.1, "top_k": 6},
                "performance_mode": False,
            },
        },
    )
    assert response.status_code == 200
    return str(response.json()["run_id"])


def _wait_for_run(client: TestClient, run_id: str) -> dict[str, object]:
    for _ in range(240):
        run = client.get(f"/api/runs/{run_id}").json()
        if run["status"] in {"succeeded", "failed", "partial_budget_exceeded"}:
            return run
        time.sleep(0.03)
    raise AssertionError("Run did not complete in time")


def test_advanced_run_endpoints_include_corpus_citations_and_trace_steps(tmp_path: Path) -> None:
    corpus_root = tmp_path / "corpus"
    corpus_root.mkdir()
    (corpus_root / "retry_policy.py").write_text("class RetryPolicy:\n    max_attempts = 5\n")
    (corpus_root / "api.py").write_text("from retry_policy import RetryPolicy\n")

    app = create_app()
    with TestClient(app) as client:
        corpus_id = _create_corpus(client, corpus_root)
        job_id = _start_index(client, corpus_id)
        job = _wait_for_index(client, job_id)
        assert job["status"] == "succeeded"

        run_id = _start_run(client, corpus_id, "where retry policy")
        run = _wait_for_run(client, run_id)
        assert run["status"] in {"succeeded", "partial_budget_exceeded"}
        assert isinstance(run["citations"], list)
        if run["citations"]:
            assert run["citations"][0]["corpus_id"] == corpus_id

        citations = client.get(f"/api/runs/{run_id}/citations")
        assert citations.status_code == 200
        citation_payload = citations.json()
        if citation_payload:
            assert citation_payload[0]["corpus_id"] == corpus_id

        trace_summary = client.get(f"/api/runs/{run_id}/trace/summary")
        assert trace_summary.status_code == 200
        summary_payload = trace_summary.json()
        assert summary_payload["events_total"] >= 1
        assert isinstance(summary_payload["type_counts"], dict)

        latest_step = client.get(f"/api/runs/{run_id}/trace/step")
        assert latest_step.status_code == 200
        latest_payload = latest_step.json()
        assert latest_payload["seq"] >= 1
        assert isinstance(latest_payload["payload"], dict)

        missing_step = client.get(f"/api/runs/{run_id}/trace/step?seq=99999")
        assert missing_step.status_code == 404

        share = client.get(f"/api/runs/{run_id}/share")
        assert share.status_code == 200
        share_payload = share.json()
        assert share_payload["run"]["run_id"] == run_id
        assert "trace" in share_payload


def test_compare_runs_returns_overlap_metrics(tmp_path: Path) -> None:
    corpus_root = tmp_path / "corpus"
    corpus_root.mkdir()
    (corpus_root / "retry_policy.py").write_text("class RetryPolicy:\n    max_attempts = 5\n")
    (corpus_root / "api.py").write_text("from retry_policy import RetryPolicy\n")

    app = create_app()
    with TestClient(app) as client:
        corpus_id = _create_corpus(client, corpus_root)
        job_id = _start_index(client, corpus_id)
        job = _wait_for_index(client, job_id)
        assert job["status"] == "succeeded"

        run_a = _start_run(client, corpus_id, "where retry policy")
        run_b = _start_run(client, corpus_id, "summarize architecture")
        _wait_for_run(client, run_a)
        _wait_for_run(client, run_b)

        compare = client.post("/api/runs/compare", json={"left_run_id": run_a, "right_run_id": run_b})
        assert compare.status_code == 200
        compare_payload = compare.json()
        assert "compare_id" in compare_payload
        assert "comparison" in compare_payload
        assert "overlap_ratio" in compare_payload["comparison"]

        compare_id = compare_payload["compare_id"]
        fetched = client.get(f"/api/runs/compare/{compare_id}")
        assert fetched.status_code == 200
        fetched_payload = fetched.json()
        assert fetched_payload["comparison"]["left_run_id"] == run_a
        assert fetched_payload["comparison"]["right_run_id"] == run_b


def test_watch_policy_and_eval_endpoints(tmp_path: Path) -> None:
    corpus_root = tmp_path / "corpus"
    corpus_root.mkdir()
    (corpus_root / "contacts.txt").write_text("Contact: jane.doe@example.com\nToken: sk-ABCDEFGHIJKLMNOPQRSTUVWXYZ1234\n")
    (corpus_root / "retry_policy.py").write_text("class RetryPolicy:\n    max_attempts = 5\n")

    app = create_app()
    with TestClient(app) as client:
        corpus_id = _create_corpus(client, corpus_root)
        job_id = _start_index(client, corpus_id)
        job = _wait_for_index(client, job_id)
        assert job["status"] == "succeeded"

        watch_start = client.post(f"/api/corpora/{corpus_id}/watch/start", json={"poll_interval_s": 3})
        assert watch_start.status_code == 200
        assert watch_start.json()["status"] in {"running", "error"}

        watch_status = client.get(f"/api/corpora/{corpus_id}/watch")
        assert watch_status.status_code == 200
        assert watch_status.json()["corpus_id"] == corpus_id

        watchers = client.get("/api/watchers")
        assert watchers.status_code == 200
        assert any(item["corpus_id"] == corpus_id for item in watchers.json())

        policy_summary = client.get(f"/api/corpora/{corpus_id}/policy/summary")
        assert policy_summary.status_code == 200
        assert policy_summary.json()["total_findings"] >= 1

        policy_findings = client.get(f"/api/corpora/{corpus_id}/policy/findings?limit=10")
        assert policy_findings.status_code == 200
        findings_payload = policy_findings.json()
        assert len(findings_payload) >= 1
        assert "category" in findings_payload[0]

        eval_create = client.post(
            "/api/evals",
            json={
                "corpus_id": corpus_id,
                "queries": ["where retry policy"],
                "runtime": {
                    "provider": "openai",
                    "model": "gpt-5-nano",
                    "environment": "docker",
                    "max_depth": 2,
                    "max_iterations": 2,
                    "budgets": {"max_wall_time_s": 60, "max_subcalls": 20},
                },
            },
        )
        assert eval_create.status_code == 200
        eval_id = eval_create.json()["eval_id"]

        eval_detail_payload: dict[str, object] | None = None
        for _ in range(200):
            eval_detail = client.get(f"/api/evals/{eval_id}")
            assert eval_detail.status_code == 200
            eval_detail_payload = eval_detail.json()
            if eval_detail_payload["status"] in {"succeeded", "failed"}:
                break
            time.sleep(0.03)
        assert eval_detail_payload is not None
        assert eval_detail_payload["status"] == "succeeded"

        eval_list = client.get("/api/evals")
        assert eval_list.status_code == 200
        assert any(item["eval_id"] == eval_id for item in eval_list.json())

        watch_stop = client.post(f"/api/corpora/{corpus_id}/watch/stop")
        assert watch_stop.status_code == 200
        assert watch_stop.json()["status"] in {"stopped", "error"}
