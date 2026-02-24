# RLM-Lens Backend

FastAPI backend for corpus indexing, recursive runtime execution, trace capture, and export/share APIs.

## Local dev
```bash
cd backend
uv sync --group dev
uv run python -m rlm_lens.main
```

## Production container
Dockerfile: `backend/Dockerfile`

Key env vars:
- `OPENAI_API_KEY`
- `RLM_LENS_BACKEND_HOST`
- `RLM_LENS_BACKEND_PORT`
- `RLM_LENS_DATA_DIR`
- `RLM_LENS_CORS_ORIGINS`

## Health endpoint
- `GET /api/health`
