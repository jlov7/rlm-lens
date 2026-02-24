# API Spec — RLM-Lens (v1)

Base URL: `http://127.0.0.1:8765`

## Conventions
- All timestamps ISO8601.
- IDs are short UUIDs.
- Errors use:
  - HTTP status
  - JSON body: `{ "error": { "code": "...", "message": "...", "details": {...} } }`

## 1. Health
### GET `/api/health`
Response 200:
```json
{ "status": "ok", "version": "0.1.0" }
```

### GET `/api/diagnostics`
Returns local runtime readiness and provider key presence for frontend warnings.
Provider entries advertise selectable options; real execution compatibility is validated at run time and unsupported combinations degrade to fallback warnings.

Response 200:
```json
{
  "provider": {
    "selected": "openai",
    "openai_api_key_present": true,
    "keys_present": {
      "openai": true,
      "anthropic": false,
      "gemini": false,
      "xai": false,
      "openrouter": false,
      "together": false,
      "groq": false,
      "fireworks": false
    },
    "available": [
      {
        "id": "openai",
        "label": "OpenAI",
        "transport": "native",
        "default_model": "gpt-5-nano",
        "recommended_models": ["gpt-5-mini", "gpt-5-nano"],
        "key_env_var": "OPENAI_API_KEY",
        "key_env_vars": ["OPENAI_API_KEY"],
        "key_present": true
      }
    ],
    "byok_header_supported": true,
    "byok_header_name": "X-RLM-LENS-PROVIDER-KEY",
    "session_key_storage": "ephemeral_request_header_only"
  },
  "environment": { "docker_installed": true, "docker_running": true }
}
```

## 1.5 Starter corpora
### GET `/api/starter-corpora`
Returns curated starter packs for onboarding/demo bootstrap.

Response 200:
```json
[
  {
    "id": "fixture-small",
    "name": "Fixture Corpus",
    "size_label": "Small",
    "approx_files": 8,
    "installed": true,
    "path": "/abs/path/.rlm-lens/starter-corpora/fixture-small"
  }
]
```

### POST `/api/starter-corpora/{pack_id}/materialize`
Downloads/generates/copies starter corpus data into local data storage.

Optional request:
```json
{ "force": false }
```

Response 200:
```json
{
  "pack_id": "synthetic-medium",
  "name": "Synthetic Engineering Corpus",
  "path": "/abs/path/.rlm-lens/starter-corpora/synthetic-medium",
  "installed": true,
  "already_present": false,
  "files_total": 189,
  "bytes_total": 240381
}
```

## 2. Corpora
### POST `/api/corpora`
Create a corpus record (and optionally start indexing).
Request:
```json
{
  "name": "My Repo",
  "path": "/Users/me/projects/repo",
  "index_config": {
    "include_globs": ["**/*.md", "**/*.py", "**/*.ts", "**/*.tsx"],
    "exclude_globs": ["**/node_modules/**", "**/.git/**"],
    "max_file_bytes": 1000000
  },
  "start_index": true
}
```

Response:
```json
{ "corpus_id": "cor_abc123", "index_job_id": "job_def456" }
```

### GET `/api/corpora`
List corpora.

### GET `/api/corpora/{corpus_id}`
Get corpus details incl. index status.

## 3. Indexing jobs
### POST `/api/index`
Start indexing an existing corpus.
Request:
```json
{ "corpus_id": "cor_abc123" }
```
Response:
```json
{ "index_job_id": "job_def456" }
```

### GET `/api/index/{index_job_id}`
Get job status:
```json
{
  "job_id": "job_def456",
  "status": "running",
  "progress": { "files_total": 1200, "files_done": 450, "current_path": "src/app.py" },
  "started_at": "...",
  "finished_at": null
}
```

### GET `/api/index/{index_job_id}/events` (SSE)
Stream indexing progress events:
- `index.progress`
- `index.warn`
- `index.complete`

Event payload example:
```json
{ "type": "index.progress", "files_done": 450, "files_total": 1200, "current_path": "src/app.py" }
```

## 4. Runs
### POST `/api/runs`
Start a run (chat query).

Optional header for hosted BYOK:
- `X-RLM-LENS-PROVIDER-KEY: <user key>`
- Behavior: key is used for that run only and is not persisted in DB/runtime config.
- Trust boundary: hosted backend/edge infrastructure still terminates the request and can observe headers in transit/log pipelines.

Request:
```json
{
  "corpus_id": "cor_abc123",
  "messages": [
    { "role": "user", "content": "Where is the retry policy defined?" }
  ],
  "runtime": {
    "provider": "openai",
    "model": "gpt-5-nano",
    "environment": "docker",
    "max_depth": 2,
    "max_iterations": 10,
    "performance_mode": false,
    "target_corpora": ["cor_secondary"],
    "corpus_weights": { "cor_abc123": 1.0, "cor_secondary": 0.7 },
    "retrieval": {
      "bm25_weight": 0.55,
      "vector_weight": 0.35,
      "rerank_weight": 0.10,
      "top_k": 6
    },
    "budgets": { "max_wall_time_s": 90, "max_subcalls": 40 }
  }
}
```

Response:
```json
{ "run_id": "run_01H...", "status": "running" }
```

### GET `/api/runs`
List runs (filters: corpus_id, status, q).

### GET `/api/runs/{run_id}`
Run details:
- messages
- final answer
- citations
- usage summary
- status

`usage` may include:
- `warnings`: runtime fallback warnings shown in UI
- `grounding`: claim-to-citation overlap report with `grounding_score`

### GET `/api/runs/{run_id}/events` (WS preferred; SSE allowed)
Live stream run events.
Event types (minimum):
- `run.metadata`
- `run.iteration`
- `run.code_block`
- `run.subcall`
- `run.budget`
- `run.error`
- `run.complete`

### GET `/api/runs/{run_id}/trace`
Return trace as JSON (or paginated).
Prefer `?format=jsonl` to download raw trace file.

### GET `/api/runs/{run_id}/trace/summary`
Returns derived telemetry for the trace:
- event totals
- type counts
- iteration ids observed
- first/last timestamps

### GET `/api/runs/{run_id}/trace/step?seq={n}`
Returns one specific trace step (or latest when `seq` is omitted).

### POST `/api/runs/{run_id}/replay`
Replay a prior run (same config and corpus snapshot hash if available).
Response: `{ "run_id": "run_new...", "status": "running" }`

### POST `/api/runs/compare`
Compares two runs and stores a reusable comparison artifact.

Request:
```json
{ "left_run_id": "run_A", "right_run_id": "run_B" }
```

Response:
```json
{
  "compare_id": "cmp_123",
  "comparison": {
    "left_run_id": "run_A",
    "right_run_id": "run_B",
    "overlap_ratio": 0.667,
    "overlap_paths": ["cor_abc123:src/retry.py"]
  }
}
```

### GET `/api/runs/compare/{compare_id}`
Fetches a saved run comparison by id.

## 5. Evidence & citations
### GET `/api/runs/{run_id}/citations`
Response:
```json
[
  {
    "citation_id": "cit_...",
    "corpus_id": "cor_abc123",
    "path": "src/retry.py",
    "start_line": 120,
    "end_line": 155,
    "snippet": "..."
  }
]
```

### GET `/api/files/slice`
Query params: `corpus_id`, `path`, `start_line`, `end_line`
Response:
```json
{ "path": "...", "start_line": 120, "end_line": 155, "text": "...", "content_hash": "sha256:..." }
```

## 6. Watchers & policy
### POST `/api/corpora/{corpus_id}/watch/start`
Starts filesystem watch-driven reindexing.

Optional request payload:
```json
{ "poll_interval_s": 12 }
```

### POST `/api/corpora/{corpus_id}/watch/stop`
Stops watcher loop for the corpus.

### GET `/api/corpora/{corpus_id}/watch`
Returns watcher status for one corpus.

### GET `/api/watchers`
Returns watcher status for all corpora.

### GET `/api/corpora/{corpus_id}/policy/summary`
Returns aggregated sensitive-data findings discovered during indexing.

### GET `/api/corpora/{corpus_id}/policy/findings?limit=200`
Returns individual findings (`path`, `line_no`, `category`, `severity`, `preview`).

## 7. Evals
### POST `/api/evals`
Creates and starts an evaluation run over one corpus.

Request:
```json
{
  "corpus_id": "cor_abc123",
  "queries": ["where retry policy", "summarize architecture"],
  "runtime": {
    "provider": "openai",
    "model": "gpt-5-nano",
    "environment": "docker",
    "max_depth": 2,
    "max_iterations": 4,
    "budgets": { "max_wall_time_s": 90, "max_subcalls": 40 }
  }
}
```

### GET `/api/evals`
Lists recent eval runs with summary metrics.

### GET `/api/evals/{eval_id}`
Returns full eval detail including per-query run outputs.

## 8. Export
### POST `/api/runs/{run_id}/export`
Response:
```json
{ "export_id": "exp_...", "zip_path": ".rlm-lens/exports/run_...zip" }
```

### GET `/api/exports/{export_id}`
Download metadata and optionally the zip.

### GET `/api/runs/{run_id}/share`
Returns a share payload (run, citations, trace stats) used by frontend share preview and standalone export viewer.

## 9. Settings
### GET `/api/settings`
### POST `/api/settings`
Store local defaults (non-secret). Secrets via env vars only.
