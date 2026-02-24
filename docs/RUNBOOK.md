# Runbook — RLM-Lens (Local Ops)

## 1. Common commands
- Start dev: `make dev`
- Verify: `make check`
- Smoke E2E: `make e2e`
- Deterministic visual gate: `make verify-visual`
- Demo: `make demo`
- Starter packs: `make starter-corpora`
- Reset state: delete `./.rlm-lens/` (destructive)

## 2. Data locations
- SQLite DB: `./.rlm-lens/db.sqlite`
- Runs: `./.rlm-lens/runs/<run_id>/`
- Exports: `./.rlm-lens/exports/`
- Starter corpora: `./.rlm-lens/starter-corpora/<pack_id>/`

## 3. Logs
Backend logs:
- Console output (dev)
- Optional file logs: `./.rlm-lens/logs/backend.log`

Frontend logs:
- Browser console (devtools)

## 4. Diagnosing a failed run
1. Open run details page in UI
2. Inspect:
   - error banner
   - trace node marked “error”
   - runtime warning banners (missing key, docker fallback, disconnect)
3. Download trace JSONL and search for:
   - `stderr`
   - `error`
   - provider error codes

4. Validate readiness quickly:
   - `GET /api/diagnostics` for API key and docker status
   - `GET /api/health` for backend liveness

## 5. Index rebuild
- Trigger reindex from UI Settings or `POST /api/index`
- If index corrupted, stop server and delete:
  - `./.rlm-lens/db.sqlite`
  - `./.rlm-lens/index/` (if used)

## 6. Updating dependencies
- Backend: `uv sync` or `uv pip compile` depending on setup
- Frontend: `pnpm up`

## 7. Backup & sharing
- Export bundles are the recommended artifact to share.
- For sharing a corpus snapshot (not recommended), share only the manifest, not the full index.

## 8. Watchers, policy, and eval ops
- Start watcher: `POST /api/corpora/{corpus_id}/watch/start` with optional `poll_interval_s`.
- Stop watcher: `POST /api/corpora/{corpus_id}/watch/stop`.
- Inspect watcher status:
  - corpus-scoped: `GET /api/corpora/{corpus_id}/watch`
  - global: `GET /api/watchers`
- Review policy findings:
  - summary: `GET /api/corpora/{corpus_id}/policy/summary`
  - findings: `GET /api/corpora/{corpus_id}/policy/findings?limit=200`
- Run corpus eval:
  - create: `POST /api/evals`
  - list: `GET /api/evals`
  - detail: `GET /api/evals/{eval_id}`

## 9. Run comparison and trace drilldown
- Compare runs:
  - `POST /api/runs/compare` with `left_run_id` and `right_run_id`
  - fetch saved comparison: `GET /api/runs/compare/{compare_id}`
- Trace summary:
  - `GET /api/runs/{run_id}/trace/summary`
- Trace step:
  - latest: `GET /api/runs/{run_id}/trace/step`
  - by sequence: `GET /api/runs/{run_id}/trace/step?seq={n}`

## 10. Starter corpus operations
- List packs:
  - `GET /api/starter-corpora`
  - `uv run python -m rlm_lens.starter_corpora_cli list`
- Materialize a pack:
  - `POST /api/starter-corpora/{pack_id}/materialize`
  - `uv run python -m rlm_lens.starter_corpora_cli materialize --pack synthetic-medium`
- Force re-create:
  - `uv run python -m rlm_lens.starter_corpora_cli materialize --pack synthetic-medium --force`
