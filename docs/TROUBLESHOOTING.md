# Troubleshooting — RLM-Lens

## 1. Setup & environment

### 1.1 “OPENAI_API_KEY is missing”
Symptoms:
- Provider connection test fails
- Runs fail immediately with auth error

Fix:
1. Copy `.env.example` → `.env`
2. Set `OPENAI_API_KEY=...`
3. Restart backend (`make dev`)

### 1.2 “uv not found”
Fix:
- Install uv via Astral’s installer or package manager
- Alternatively, use `python -m venv .venv` and install dependencies manually (not recommended)

### 1.3 “pnpm not found”
Fix:
- Install pnpm (corepack recommended)
- Verify: `pnpm -v`

### 1.4 Port already in use
Backend default: 8765
Frontend default: 5173 (dev) or 3000 (preview)

Fix:
- Stop other processes or change ports in `.env`

## 2. Docker / sandbox issues

### 2.1 “Docker not installed or not running”
If Docker sandbox is default, RLM-Lens should automatically fallback to local sandbox and show a warning.

Fix:
- Install Docker Desktop and start it
- Re-run the run

### 2.2 Permission errors mounting volumes
Fix:
- Ensure the corpus folder is shared with Docker Desktop
- Avoid indexing protected OS directories

## 3. Indexing issues

### 3.1 Index is empty / missing files
Common causes:
- exclude globs too broad
- max_file_bytes too small
- files are binary or unsupported encoding

Fix:
- Review index config in Settings
- Rebuild index

### 3.2 Slow indexing
Fixes:
- Increase max_file_bytes only if needed
- Exclude large vendor folders
- Ensure disk isn’t under heavy load

### 3.3 SQLite “database is locked”
Fix:
- Ensure only one backend instance is running
- Delete `.rlm-lens/db.sqlite` and rebuild (last resort)

## 4. Query/runtime issues

### 4.1 “Budget exceeded”
Expected when budgets are small.

Fix:
- Increase `max_wall_time_s` or `max_subcalls`
- Narrow the question (“in src/ only…”)

### 4.2 Garbage citations
Fix:
- Ensure citations are generated from `lens.read` line ranges
- Rebuild index if files changed drastically
- In code: improve citation parser to validate line ranges exist

### 4.3 Provider errors or rate limits
Fix:
- Reduce concurrency
- Use smaller model
- Implement retry with backoff for transient errors

## 5. Frontend issues

### 5.1 Trace graph is blank
Fix:
- Confirm WS/SSE connection in browser devtools
- Check backend logs for event streaming errors
- Ensure `/api/runs/{id}/events` is reachable

### 5.2 Evidence viewer doesn’t open
Fix:
- Validate citation payload includes corpus_id/path/start_line/end_line
- Verify file slice endpoint returns content

## 6. Developer workflow

### 6.1 `make check` fails
Fix:
- Run the failing command directly (printed by Makefile)
- Fix lint/type/test; rerun until green

### 6.2 E2E tests flaky
Fix:
- Increase Playwright timeouts for indexing
- Use the demo corpus to keep runtime stable

## 7. Starter corpus issues

### 7.1 Starter pack download fails
Symptoms:
- Materialize action fails in onboarding
- API returns 400 during `/api/starter-corpora/{id}/materialize`

Fix:
1. Try an offline pack (`fixture-small` or `synthetic-medium`)
2. Verify outbound internet access for remote packs
3. Retry with force: `uv run python -m rlm_lens.starter_corpora_cli materialize --pack <id> --force`

### 7.2 Starter pack appears installed but content is missing
Fix:
1. Recreate with `--force`
2. Verify data directory path (`RLM_LENS_DATA_DIR`)
3. Ensure process has write permissions

## 8. Deployment issues (Vercel + Railway)

### 8.1 Frontend loads but API calls fail (CORS)
Fix:
1. Set backend `RLM_LENS_CORS_ORIGINS` to exact Vercel domain(s)
2. Redeploy Railway service
3. Confirm browser network errors are resolved

### 8.2 Vercel points to wrong backend
Fix:
1. Set `VITE_API_BASE` in Vercel project env vars
2. Trigger redeploy
3. Validate `/api/health` via frontend network panel

### 8.3 Railway data resets after restart
Fix:
1. Attach persistent volume
2. Set `RLM_LENS_DATA_DIR` to mounted volume path
3. Re-run starter corpus materialization/indexing once

### 8.4 Railway deployment stuck on healthcheck
Symptoms:
- Service reaches `DEPLOYING` then fails healthcheck retries.

Fix:
1. Ensure service listens on expected runtime port:
   - set `PORT=8765`
   - leave `RLM_LENS_BACKEND_PORT` unset (or set it to match `PORT`)
2. Ensure host bind is public:
   - `RLM_LENS_BACKEND_HOST=0.0.0.0`
3. Redeploy and recheck:
   - `railway up -s backend --detach`

### 8.5 Vercel build fails with pnpm lockfile compatibility
Symptoms:
- Build logs show `Ignoring not compatible lockfile` or pnpm `ERR_INVALID_THIS`.

Fix:
1. Use npm install/build commands in `vercel.json` for cloud builds.
2. Keep local development on pnpm unchanged.
