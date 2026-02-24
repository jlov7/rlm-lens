from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse, StreamingResponse
import json
from pathlib import Path
from typing import Any

from ..ids import make_id
from ..models import CreateCorpusRequest, CreateRunRequest
from ..providers import SESSION_PROVIDER_KEY_HEADER, build_provider_diagnostics, normalize_provider_api_key
from ..runtime.environment import get_environment_status
from ..utils import now_iso
from .common import get_services, sse_response

router = APIRouter(prefix="/api")


def _json_loads(value: object, fallback: object) -> object:
    try:
        return json.loads(str(value))
    except (TypeError, ValueError, json.JSONDecodeError):
        return fallback


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": "0.1.0"}


@router.get("/diagnostics")
async def diagnostics(selected_provider: str | None = Query(default=None)) -> dict[str, object]:
    env_status = get_environment_status()
    return {
        "provider": build_provider_diagnostics(selected_provider=selected_provider),
        "environment": {
            "docker_installed": env_status.docker_installed,
            "docker_running": env_status.docker_running,
        },
    }


@router.get("/starter-corpora")
async def list_starter_corpora(request: Request) -> list[dict[str, object]]:
    services = get_services(request)
    return services.starter_corpora.list_packs()


@router.post("/starter-corpora/{pack_id}/materialize")
async def materialize_starter_corpus(
    pack_id: str,
    request: Request,
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    services = get_services(request)
    force = bool((payload or {}).get("force", False))
    try:
        return services.starter_corpora.materialize(pack_id=pack_id, force=force)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/corpora")
async def create_corpus(payload: CreateCorpusRequest, request: Request) -> dict[str, str | None]:
    services = get_services(request)
    corpus_id = make_id("cor")
    now = now_iso()
    services.db.execute(
        """
        INSERT INTO corpora (id, name, root_path, created_at, updated_at, index_config_json)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (corpus_id, payload.name, str(Path(payload.path).resolve()), now, now, payload.index_config.model_dump_json()),
    )

    job_id: str | None = None
    if payload.start_index:
        job_id = services.indexer.create_job(corpus_id)
        services.spawn(services.indexer.run_job(job_id))

    return {"corpus_id": corpus_id, "index_job_id": job_id}


@router.get("/corpora")
async def list_corpora(request: Request) -> list[dict[str, object]]:
    services = get_services(request)
    rows = services.db.fetchall("SELECT id, name, root_path, created_at, updated_at, last_indexed_at, last_snapshot_hash, latest_index_summary_json FROM corpora ORDER BY created_at DESC")
    return [
        {
            "id": str(row["id"]),
            "name": str(row["name"]),
            "path": str(row["root_path"]),
            "created_at": str(row["created_at"]),
            "updated_at": str(row["updated_at"]),
            "last_indexed_at": row["last_indexed_at"],
            "last_snapshot_hash": row["last_snapshot_hash"],
            "index_summary": json.loads(str(row["latest_index_summary_json"] or "{}")),
        }
        for row in rows
    ]


@router.get("/corpora/{corpus_id}")
async def get_corpus(corpus_id: str, request: Request) -> dict[str, object]:
    services = get_services(request)
    row = services.db.fetchone(
        "SELECT id, name, root_path, index_config_json, created_at, updated_at, last_index_job_id, last_indexed_at, last_snapshot_hash, latest_index_summary_json FROM corpora WHERE id = ?",
        (corpus_id,),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Corpus not found")

    return {
        "id": str(row["id"]),
        "name": str(row["name"]),
        "path": str(row["root_path"]),
        "index_config": json.loads(str(row["index_config_json"])),
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
        "last_index_job_id": row["last_index_job_id"],
        "last_indexed_at": row["last_indexed_at"],
        "last_snapshot_hash": row["last_snapshot_hash"],
        "index_summary": json.loads(str(row["latest_index_summary_json"] or "{}")),
    }


@router.post("/corpora/{corpus_id}/watch/start")
async def start_corpus_watch(
    corpus_id: str,
    request: Request,
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    services = get_services(request)
    if services.db.fetchone("SELECT id FROM corpora WHERE id = ?", (corpus_id,)) is None:
        raise HTTPException(status_code=404, detail="Corpus not found")
    raw_interval = (payload or {}).get("poll_interval_s", 20)
    if isinstance(raw_interval, bool):
        poll_interval_s = 20
    elif isinstance(raw_interval, int):
        poll_interval_s = raw_interval
    elif isinstance(raw_interval, str):
        try:
            poll_interval_s = int(raw_interval)
        except ValueError:
            poll_interval_s = 20
    else:
        poll_interval_s = 20
    services.watch_manager.start(corpus_id=corpus_id, poll_interval_s=max(3, poll_interval_s))
    status = services.watch_manager.status(corpus_id)
    return status or {"corpus_id": corpus_id, "status": "running"}


@router.post("/corpora/{corpus_id}/watch/stop")
async def stop_corpus_watch(corpus_id: str, request: Request) -> dict[str, object]:
    services = get_services(request)
    if services.db.fetchone("SELECT id FROM corpora WHERE id = ?", (corpus_id,)) is None:
        raise HTTPException(status_code=404, detail="Corpus not found")
    services.watch_manager.stop(corpus_id=corpus_id)
    status = services.watch_manager.status(corpus_id)
    return status or {"corpus_id": corpus_id, "status": "stopped"}


@router.get("/corpora/{corpus_id}/watch")
async def get_corpus_watch(corpus_id: str, request: Request) -> dict[str, object]:
    services = get_services(request)
    if services.db.fetchone("SELECT id FROM corpora WHERE id = ?", (corpus_id,)) is None:
        raise HTTPException(status_code=404, detail="Corpus not found")
    status = services.watch_manager.status(corpus_id)
    if status is None:
        return {"corpus_id": corpus_id, "status": "stopped", "poll_interval_s": 20}
    return status


@router.get("/watchers")
async def list_watchers(request: Request) -> list[dict[str, object]]:
    services = get_services(request)
    return services.watch_manager.list_status()


@router.get("/corpora/{corpus_id}/policy/summary")
async def get_policy_summary(corpus_id: str, request: Request) -> dict[str, object]:
    services = get_services(request)
    if services.db.fetchone("SELECT id FROM corpora WHERE id = ?", (corpus_id,)) is None:
        raise HTTPException(status_code=404, detail="Corpus not found")
    return services.policy.policy_summary(corpus_id)


@router.get("/corpora/{corpus_id}/policy/findings")
async def get_policy_findings(
    corpus_id: str,
    request: Request,
    limit: int = Query(default=200, ge=1, le=1000),
) -> list[dict[str, object]]:
    services = get_services(request)
    if services.db.fetchone("SELECT id FROM corpora WHERE id = ?", (corpus_id,)) is None:
        raise HTTPException(status_code=404, detail="Corpus not found")
    return services.policy.list_findings(corpus_id=corpus_id, limit=limit)


@router.post("/index")
async def start_index(payload: dict[str, str], request: Request) -> dict[str, str]:
    services = get_services(request)
    corpus_id = payload.get("corpus_id", "")
    exists = services.db.fetchone("SELECT id FROM corpora WHERE id = ?", (corpus_id,))
    if exists is None:
        raise HTTPException(status_code=404, detail="Corpus not found")

    job_id = services.indexer.create_job(corpus_id)
    services.spawn(services.indexer.run_job(job_id))
    return {"index_job_id": job_id}


@router.get("/index/{job_id}")
async def get_index_job(job_id: str, request: Request) -> dict[str, object]:
    services = get_services(request)
    row = services.db.fetchone(
        "SELECT id, corpus_id, status, started_at, finished_at, progress_json, summary_json, error_json FROM index_jobs WHERE id = ?",
        (job_id,),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Index job not found")

    return {
        "job_id": str(row["id"]),
        "corpus_id": str(row["corpus_id"]),
        "status": str(row["status"]),
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
        "progress": json.loads(str(row["progress_json"] or "{}")),
        "summary": json.loads(str(row["summary_json"] or "{}")),
        "error": json.loads(str(row["error_json"] or "null")),
    }


@router.get("/index/{job_id}/events", response_model=None)
async def stream_index_events(job_id: str, request: Request) -> StreamingResponse:
    services = get_services(request)
    if services.db.fetchone("SELECT id FROM index_jobs WHERE id = ?", (job_id,)) is None:
        raise HTTPException(status_code=404, detail="Index job not found")
    return sse_response(services.broker.subscribe("index", job_id))


@router.post("/runs")
async def create_run(payload: CreateRunRequest, request: Request) -> dict[str, str]:
    services = get_services(request)
    if services.db.fetchone("SELECT id FROM corpora WHERE id = ?", (payload.corpus_id,)) is None:
        raise HTTPException(status_code=404, detail="Corpus not found")

    provider_api_key = normalize_provider_api_key(request.headers.get(SESSION_PROVIDER_KEY_HEADER))
    run_id = make_id("run")
    snapshot_hash = services.db.fetch_value("SELECT last_snapshot_hash FROM corpora WHERE id = ?", (payload.corpus_id,))
    services.db.execute(
        """
        INSERT INTO runs (id, corpus_id, snapshot_hash, status, created_at, runtime_config_json)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (run_id, payload.corpus_id, str(snapshot_hash or ""), "running", now_iso(), payload.runtime.model_dump_json()),
    )

    for message in payload.messages:
        services.db.execute(
            "INSERT INTO messages (run_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (run_id, message.role, message.content, now_iso()),
        )

    services.spawn(services.runner.run(run_id, provider_api_key=provider_api_key))
    return {"run_id": run_id, "status": "running"}


@router.get("/runs")
async def list_runs(
    request: Request,
    corpus_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    q: str | None = Query(default=None),
) -> list[dict[str, object]]:
    services = get_services(request)
    clauses: list[str] = []
    params: list[str] = []
    if corpus_id:
        clauses.append("corpus_id = ?")
        params.append(corpus_id)
    if status:
        clauses.append("status = ?")
        params.append(status)
    if q:
        clauses.append("id IN (SELECT run_id FROM messages WHERE role = 'user' AND content LIKE ?)")
        params.append(f"%{q}%")

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = services.db.fetchall(
        f"SELECT id, corpus_id, status, created_at, started_at, finished_at, usage_json, final_answer_md FROM runs {where} ORDER BY created_at DESC",
        tuple(params),
    )

    return [
        {
            "id": str(row["id"]),
            "corpus_id": str(row["corpus_id"]),
            "status": str(row["status"]),
            "created_at": str(row["created_at"]),
            "started_at": row["started_at"],
            "finished_at": row["finished_at"],
            "usage": json.loads(str(row["usage_json"] or "{}")),
            "answer_preview": (str(row["final_answer_md"] or "")[:220]),
        }
        for row in rows
    ]


@router.post("/runs/compare")
async def compare_runs(payload: dict[str, str], request: Request) -> dict[str, object]:
    services = get_services(request)
    left_run_id = payload.get("left_run_id")
    right_run_id = payload.get("right_run_id")
    if not left_run_id or not right_run_id:
        raise HTTPException(status_code=400, detail="left_run_id and right_run_id are required")

    left_run = services.db.fetchone("SELECT id, status, usage_json, final_answer_md FROM runs WHERE id = ?", (left_run_id,))
    right_run = services.db.fetchone("SELECT id, status, usage_json, final_answer_md FROM runs WHERE id = ?", (right_run_id,))
    if left_run is None or right_run is None:
        raise HTTPException(status_code=404, detail="One or both runs not found")

    left_citations = services.db.fetchall("SELECT corpus_id, path, start_line, end_line FROM citations WHERE run_id = ?", (left_run_id,))
    right_citations = services.db.fetchall("SELECT corpus_id, path, start_line, end_line FROM citations WHERE run_id = ?", (right_run_id,))

    left_paths = {f"{(row['corpus_id'] or '')!s}:{row['path']!s}" for row in left_citations}
    right_paths = {f"{(row['corpus_id'] or '')!s}:{row['path']!s}" for row in right_citations}
    overlap_paths = sorted(left_paths.intersection(right_paths))

    left_usage = _json_loads(left_run["usage_json"], {})
    right_usage = _json_loads(right_run["usage_json"], {})
    if not isinstance(left_usage, dict):
        left_usage = {}
    if not isinstance(right_usage, dict):
        right_usage = {}

    compare_payload = {
        "left_run_id": str(left_run["id"]),
        "right_run_id": str(right_run["id"]),
        "left_status": str(left_run["status"]),
        "right_status": str(right_run["status"]),
        "left_citations": len(left_citations),
        "right_citations": len(right_citations),
        "overlap_paths": overlap_paths,
        "overlap_ratio": round(len(overlap_paths) / max(1, len(left_paths.union(right_paths))), 3),
        "left_grounding": left_usage.get("grounding", {}).get("grounding_score") if isinstance(left_usage.get("grounding"), dict) else None,
        "right_grounding": right_usage.get("grounding", {}).get("grounding_score") if isinstance(right_usage.get("grounding"), dict) else None,
        "left_wall_time_s": left_usage.get("wall_time_s"),
        "right_wall_time_s": right_usage.get("wall_time_s"),
        "left_answer_preview": str(left_run["final_answer_md"] or "")[:220],
        "right_answer_preview": str(right_run["final_answer_md"] or "")[:220],
    }

    compare_id = make_id("cmp")
    services.db.set_setting(f"compare:{compare_id}", compare_payload)
    return {"compare_id": compare_id, "comparison": compare_payload}


@router.get("/runs/compare/{compare_id}")
async def get_compared_run(compare_id: str, request: Request) -> dict[str, object]:
    services = get_services(request)
    payload = services.db.get_setting(f"compare:{compare_id}")
    if payload is None:
        raise HTTPException(status_code=404, detail="Comparison not found")
    return {"compare_id": compare_id, "comparison": payload}


@router.get("/runs/{run_id}")
async def get_run(run_id: str, request: Request) -> dict[str, object]:
    services = get_services(request)
    run = services.db.fetchone(
        "SELECT id, corpus_id, status, runtime_config_json, final_answer_md, usage_json, error_json FROM runs WHERE id = ?",
        (run_id,),
    )
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    messages = services.db.fetchall(
        "SELECT role, content FROM messages WHERE run_id = ? ORDER BY id ASC",
        (run_id,),
    )
    citations = services.db.fetchall(
        "SELECT id, corpus_id, path, start_line, end_line, snippet FROM citations WHERE run_id = ? ORDER BY rowid ASC",
        (run_id,),
    )

    return {
        "run_id": str(run["id"]),
        "corpus_id": str(run["corpus_id"]),
        "status": str(run["status"]),
        "runtime": json.loads(str(run["runtime_config_json"])),
        "messages": [{"role": str(row["role"]), "content": str(row["content"])} for row in messages],
        "final_answer": run["final_answer_md"],
        "citations": [
            {
                "citation_id": str(row["id"]),
                "corpus_id": row["corpus_id"],
                "path": str(row["path"]),
                "start_line": int(row["start_line"]),
                "end_line": int(row["end_line"]),
                "snippet": str(row["snippet"]),
            }
            for row in citations
        ],
        "usage": json.loads(str(run["usage_json"] or "{}")),
        "error": json.loads(str(run["error_json"] or "null")),
    }


@router.get("/runs/{run_id}/events", response_model=None)
async def stream_run_events(run_id: str, request: Request) -> StreamingResponse:
    services = get_services(request)
    if services.db.fetchone("SELECT id FROM runs WHERE id = ?", (run_id,)) is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return sse_response(services.broker.subscribe("run", run_id))


@router.get("/runs/{run_id}/trace", response_model=None)
async def get_run_trace(run_id: str, request: Request, format: str | None = Query(default=None)) -> object:
    services = get_services(request)
    if services.db.fetchone("SELECT id FROM runs WHERE id = ?", (run_id,)) is None:
        raise HTTPException(status_code=404, detail="Run not found")

    trace_path = services.data_dir / "runs" / run_id / "trace.jsonl"
    if format == "jsonl":
        if not trace_path.exists():
            raise HTTPException(status_code=404, detail="Trace file not found")
        return FileResponse(path=trace_path)

    events = services.db.fetchall(
        "SELECT seq, ts, type, payload_json FROM trace_events WHERE run_id = ? ORDER BY seq ASC",
        (run_id,),
    )
    payload = [
        {
            "seq": int(row["seq"]),
            "timestamp": str(row["ts"]),
            "type": str(row["type"]),
            "payload": json.loads(str(row["payload_json"])),
        }
        for row in events
    ]
    return {"run_id": run_id, "events": payload}


@router.get("/runs/{run_id}/trace/summary")
async def get_run_trace_summary(run_id: str, request: Request) -> dict[str, object]:
    services = get_services(request)
    if services.db.fetchone("SELECT id FROM runs WHERE id = ?", (run_id,)) is None:
        raise HTTPException(status_code=404, detail="Run not found")

    rows = services.db.fetchall(
        "SELECT seq, ts, type, payload_json FROM trace_events WHERE run_id = ? ORDER BY seq ASC",
        (run_id,),
    )
    type_counts: dict[str, int] = {}
    iterations: list[int] = []
    for row in rows:
        event_type = str(row["type"])
        type_counts[event_type] = type_counts.get(event_type, 0) + 1
        payload = _json_loads(row["payload_json"], {})
        if isinstance(payload, dict):
            iteration = payload.get("iteration")
            if isinstance(iteration, int) and iteration not in iterations:
                iterations.append(iteration)

    return {
        "run_id": run_id,
        "events_total": len(rows),
        "type_counts": type_counts,
        "iterations": sorted(iterations),
        "first_event_ts": str(rows[0]["ts"]) if rows else None,
        "last_event_ts": str(rows[-1]["ts"]) if rows else None,
        "last_seq": int(rows[-1]["seq"]) if rows else None,
    }


@router.get("/runs/{run_id}/trace/step")
async def get_run_trace_step(
    run_id: str,
    request: Request,
    seq: int | None = Query(default=None, ge=1),
) -> dict[str, object]:
    services = get_services(request)
    if services.db.fetchone("SELECT id FROM runs WHERE id = ?", (run_id,)) is None:
        raise HTTPException(status_code=404, detail="Run not found")

    if seq is None:
        row = services.db.fetchone(
            "SELECT seq, ts, type, payload_json FROM trace_events WHERE run_id = ? ORDER BY seq DESC LIMIT 1",
            (run_id,),
        )
    else:
        row = services.db.fetchone(
            "SELECT seq, ts, type, payload_json FROM trace_events WHERE run_id = ? AND seq = ?",
            (run_id, seq),
        )
    if row is None:
        raise HTTPException(status_code=404, detail="Trace step not found")

    payload = _json_loads(row["payload_json"], {})
    return {
        "run_id": run_id,
        "seq": int(row["seq"]),
        "timestamp": str(row["ts"]),
        "type": str(row["type"]),
        "payload": payload if isinstance(payload, dict) else {},
    }


@router.get("/runs/{run_id}/citations")
async def get_citations(run_id: str, request: Request) -> list[dict[str, object]]:
    services = get_services(request)
    rows = services.db.fetchall(
        "SELECT id, corpus_id, path, start_line, end_line, snippet FROM citations WHERE run_id = ? ORDER BY rowid ASC",
        (run_id,),
    )
    return [
        {
            "citation_id": str(row["id"]),
            "corpus_id": row["corpus_id"],
            "path": str(row["path"]),
            "start_line": int(row["start_line"]),
            "end_line": int(row["end_line"]),
            "snippet": str(row["snippet"]),
        }
        for row in rows
    ]


@router.post("/runs/{run_id}/replay")
async def replay_run(run_id: str, request: Request) -> dict[str, str]:
    services = get_services(request)
    original = services.db.fetchone(
        "SELECT corpus_id, runtime_config_json FROM runs WHERE id = ?",
        (run_id,),
    )
    if original is None:
        raise HTTPException(status_code=404, detail="Run not found")

    messages = services.db.fetchall(
        "SELECT role, content FROM messages WHERE run_id = ? ORDER BY id ASC",
        (run_id,),
    )
    replay_id = make_id("run")
    snapshot_hash = services.db.fetch_value("SELECT last_snapshot_hash FROM corpora WHERE id = ?", (str(original["corpus_id"]),))
    services.db.execute(
        "INSERT INTO runs (id, corpus_id, snapshot_hash, status, created_at, runtime_config_json) VALUES (?, ?, ?, ?, ?, ?)",
        (replay_id, str(original["corpus_id"]), str(snapshot_hash or ""), "running", now_iso(), str(original["runtime_config_json"])),
    )
    for message in messages:
        services.db.execute(
            "INSERT INTO messages (run_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (replay_id, str(message["role"]), str(message["content"]), now_iso()),
        )

    services.spawn(services.runner.run(replay_id))
    return {"run_id": replay_id, "status": "running"}


@router.post("/runs/{run_id}/export")
async def export_run(run_id: str, request: Request) -> dict[str, str]:
    services = get_services(request)
    try:
        return services.exporter.export_run(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/runs/{run_id}/share")
async def get_run_share(run_id: str, request: Request) -> dict[str, object]:
    services = get_services(request)
    run = services.db.fetchone(
        "SELECT id, corpus_id, status, final_answer_md, runtime_config_json, usage_json, created_at, started_at, finished_at FROM runs WHERE id = ?",
        (run_id,),
    )
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    citations_rows = services.db.fetchall(
        "SELECT id, corpus_id, path, start_line, end_line, snippet FROM citations WHERE run_id = ? ORDER BY rowid ASC",
        (run_id,),
    )
    trace_rows = services.db.fetchall(
        "SELECT type, ts, seq FROM trace_events WHERE run_id = ? ORDER BY seq ASC",
        (run_id,),
    )
    type_counts: dict[str, int] = {}
    for row in trace_rows:
        event_type = str(row["type"])
        type_counts[event_type] = type_counts.get(event_type, 0) + 1

    return {
        "run": {
            "run_id": str(run["id"]),
            "corpus_id": str(run["corpus_id"]),
            "status": str(run["status"]),
            "answer": str(run["final_answer_md"] or ""),
            "runtime": _json_loads(run["runtime_config_json"], {}),
            "usage": _json_loads(run["usage_json"], {}),
            "created_at": str(run["created_at"]),
            "started_at": run["started_at"],
            "finished_at": run["finished_at"],
        },
        "citations": [
            {
                "citation_id": str(row["id"]),
                "corpus_id": row["corpus_id"],
                "path": str(row["path"]),
                "start_line": int(row["start_line"]),
                "end_line": int(row["end_line"]),
                "snippet": str(row["snippet"]),
            }
            for row in citations_rows
        ],
        "trace": {
            "events_total": len(trace_rows),
            "type_counts": type_counts,
            "first_event_ts": str(trace_rows[0]["ts"]) if trace_rows else None,
            "last_event_ts": str(trace_rows[-1]["ts"]) if trace_rows else None,
            "last_seq": int(trace_rows[-1]["seq"]) if trace_rows else None,
        },
    }


@router.get("/exports/{export_id}")
async def get_export(export_id: str, request: Request) -> dict[str, object]:
    services = get_services(request)
    row = services.db.fetchone(
        "SELECT id, run_id, created_at, zip_path, manifest_json FROM exports WHERE id = ?",
        (export_id,),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Export not found")

    return {
        "export_id": str(row["id"]),
        "run_id": str(row["run_id"]),
        "created_at": str(row["created_at"]),
        "zip_path": str(row["zip_path"]),
        "manifest": json.loads(str(row["manifest_json"])),
    }


@router.get("/files/slice")
async def get_file_slice(
    request: Request,
    corpus_id: str,
    path: str,
    start_line: int = Query(default=1),
    end_line: int = Query(default=20),
) -> dict[str, object]:
    services = get_services(request)
    try:
        return services.reader.read_slice(corpus_id=corpus_id, path=path, start_line=start_line, end_line=end_line)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/evals")
async def create_eval(payload: dict[str, object], request: Request) -> dict[str, str]:
    services = get_services(request)
    corpus_id = str(payload.get("corpus_id", "")).strip()
    if not corpus_id:
        raise HTTPException(status_code=400, detail="corpus_id is required")
    if services.db.fetchone("SELECT id FROM corpora WHERE id = ?", (corpus_id,)) is None:
        raise HTTPException(status_code=404, detail="Corpus not found")

    config: dict[str, Any] = dict(payload)
    config["corpus_id"] = corpus_id
    eval_id = services.evaluation.create_eval(config)
    services.spawn(services.evaluation.run_eval(eval_id))
    return {"eval_id": eval_id, "status": "running"}


@router.get("/evals")
async def list_evals(request: Request, limit: int = Query(default=20, ge=1, le=200)) -> list[dict[str, object]]:
    services = get_services(request)
    return services.evaluation.list_evals(limit=limit)


@router.get("/evals/{eval_id}")
async def get_eval(eval_id: str, request: Request) -> dict[str, object]:
    services = get_services(request)
    data = services.evaluation.get_eval(eval_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Eval not found")
    return data


@router.get("/settings")
async def get_settings(request: Request) -> dict[str, object]:
    services = get_services(request)
    defaults = services.db.get_setting("defaults") or {}
    return defaults


@router.post("/settings")
async def set_settings(payload: dict[str, object], request: Request) -> dict[str, object]:
    services = get_services(request)
    services.db.set_setting("defaults", payload)
    return payload
