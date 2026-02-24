from pathlib import Path
import time

from fastapi.testclient import TestClient

from rlm_lens.main import create_app


def _create_corpus_and_index(client: TestClient, corpus_root: Path) -> str:
    corpus_res = client.post(
        "/api/corpora",
        json={
            "name": "runtime-tests",
            "path": str(corpus_root),
            "index_config": {
                "include_globs": ["**/*.py", "**/*.md", "**/*.sql"],
                "exclude_globs": [],
                "max_file_bytes": 100000,
            },
            "start_index": False,
        },
    )
    assert corpus_res.status_code == 200
    corpus_id = corpus_res.json()["corpus_id"]

    index_res = client.post("/api/index", json={"corpus_id": corpus_id})
    job_id = index_res.json()["index_job_id"]
    for _ in range(120):
        job = client.get(f"/api/index/{job_id}").json()
        if job["status"] in {"succeeded", "failed"}:
            break
        time.sleep(0.02)
    assert job["status"] == "succeeded"
    return corpus_id


def _start_run(client: TestClient, corpus_id: str, question: str, max_wall_time_s: int = 90) -> str:
    run_res = client.post(
        "/api/runs",
        json={
            "corpus_id": corpus_id,
            "messages": [{"role": "user", "content": question}],
            "runtime": {
                "provider": "openai",
                "model": "gpt-5-nano",
                "environment": "docker",
                "max_depth": 2,
                "max_iterations": 6,
                "budgets": {"max_wall_time_s": max_wall_time_s, "max_subcalls": 40},
            },
        },
    )
    assert run_res.status_code == 200
    return run_res.json()["run_id"]


def _await_run(client: TestClient, run_id: str) -> dict[str, object]:
    for _ in range(240):
        run = client.get(f"/api/runs/{run_id}").json()
        if run["status"] in {"succeeded", "failed", "partial_budget_exceeded"}:
            return run
        time.sleep(0.03)
    raise AssertionError("Run did not complete in expected time")


def test_replay_creates_new_run(tmp_path: Path) -> None:
    corpus_root = tmp_path / "corpus"
    corpus_root.mkdir()
    (corpus_root / "retry_policy.py").write_text("class RetryPolicy:\n    max_attempts = 5\n")
    (corpus_root / "api.py").write_text("from retry_policy import RetryPolicy\n")

    app = create_app()
    with TestClient(app) as client:
        corpus_id = _create_corpus_and_index(client, corpus_root)
        run_id = _start_run(client, corpus_id, "where retry policy")
        first = _await_run(client, run_id)
        assert first["status"] in {"succeeded", "partial_budget_exceeded"}

        replay_res = client.post(f"/api/runs/{run_id}/replay")
        assert replay_res.status_code == 200
        replay_id = replay_res.json()["run_id"]
        assert replay_id != run_id

        replay = _await_run(client, replay_id)
        assert replay["status"] in {"succeeded", "partial_budget_exceeded"}


def test_budget_exceeded_marks_partial(tmp_path: Path) -> None:
    corpus_root = tmp_path / "corpus"
    corpus_root.mkdir()
    (corpus_root / "retry_policy.py").write_text("class RetryPolicy:\n    max_attempts = 5\n")

    app = create_app()
    with TestClient(app) as client:
        corpus_id = _create_corpus_and_index(client, corpus_root)
        run_id = _start_run(client, corpus_id, "retry policy", max_wall_time_s=0)
        run = _await_run(client, run_id)
        assert run["status"] == "partial_budget_exceeded"


def test_run_usage_includes_grounding_and_warnings(tmp_path: Path) -> None:
    corpus_root = tmp_path / "corpus"
    corpus_root.mkdir()
    (corpus_root / "retry_policy.py").write_text("class RetryPolicy:\n    max_attempts = 5\n")
    (corpus_root / "api.py").write_text("from retry_policy import RetryPolicy\n")

    app = create_app()
    with TestClient(app) as client:
        corpus_id = _create_corpus_and_index(client, corpus_root)
        run_id = _start_run(client, corpus_id, "where retry policy")
        run = _await_run(client, run_id)
        usage = run["usage"]
        assert isinstance(usage, dict)
        assert "grounding" in usage
        grounding = usage["grounding"]
        assert isinstance(grounding, dict)
        assert "grounding_score" in grounding
        assert "warnings" in usage


def test_trace_includes_metadata_and_iteration_events(tmp_path: Path) -> None:
    corpus_root = tmp_path / "corpus"
    corpus_root.mkdir()
    (corpus_root / "retry_policy.py").write_text("class RetryPolicy:\n    max_attempts = 5\n")
    (corpus_root / "api.py").write_text("from retry_policy import RetryPolicy\n")

    app = create_app()
    with TestClient(app) as client:
        corpus_id = _create_corpus_and_index(client, corpus_root)
        run_id = _start_run(client, corpus_id, "where retry policy")
        _await_run(client, run_id)

        trace_res = client.get(f"/api/runs/{run_id}/trace")
        assert trace_res.status_code == 200
        payload = trace_res.json()
        events = payload.get("events", [])
        assert isinstance(events, list)
        event_types = {item.get("type") for item in events if isinstance(item, dict)}
        assert {"metadata", "iteration"}.issubset(event_types)
        assert len(events) >= 2
