# Deployment Guide: Vercel (Frontend) + Railway (Backend)

## Recommended architecture
- Vercel: static frontend build (`frontend/dist`).
- Railway: FastAPI backend (`backend/Dockerfile`).

## 1) Deploy backend to Railway

### Files used
- `railway.json`
- `backend/Dockerfile`

### Required Railway environment variables
- `OPENAI_API_KEY`
- `RLM_LENS_BACKEND_HOST=0.0.0.0`
- `RLM_LENS_DATA_DIR=/data/rlm-lens` (attach a persistent volume)
- `RLM_LENS_CORS_ORIGINS=https://<your-vercel-domain>`

Notes:
- Railway `PORT` is supported automatically; setting `RLM_LENS_BACKEND_PORT` is optional.
- `RLM_LENS_RELOAD` defaults to off in production.

### Healthcheck
- Path: `/api/health`

## 2) Deploy frontend to Vercel

### Files used
- `vercel.json`

### Required Vercel environment variable
- `VITE_API_BASE=https://<your-railway-backend-domain>`

## 3) Post-deploy smoke checks
1. Open Vercel URL.
2. Verify onboarding loads.
3. Materialize a starter corpus pack.
4. Run query and open citation.
5. Confirm trace/events render.

## 4) Production hardening checklist
- Enable Railway volume backups.
- Restrict CORS to exact Vercel domains.
- Use separate environments for staging/prod.
- Run `make verify-visual` before release.

## 5) Live deployment status (February 24, 2026)
- Frontend (Vercel): `https://rlm-lens.vercel.app`
- Backend (Railway): `https://backend-production-4b1cb.up.railway.app`

Validated:
- `GET /api/health` returns `{"status":"ok","version":"0.1.0"}` on Railway.
- Frontend loads onboarding starter packs from backend with no browser console errors.
- Instant demo control is visible on deployed frontend.

Deployment commands used:
```bash
# Railway
railway init --name rlm-lens --workspace "Jase Lovell's Projects" --json
railway add --service backend --json
railway service link backend
railway volume add -m /data --json
railway variable set -s backend --skip-deploys \
  RLM_LENS_BACKEND_HOST=0.0.0.0 \
  RLM_LENS_DATA_DIR=/data/rlm-lens \
  RLM_LENS_RELOAD=0 \
  PORT=8765
railway variable set -s backend \
  RLM_LENS_CORS_ORIGINS=https://rlm-lens.vercel.app,http://127.0.0.1:5173,http://localhost:5173
railway up -s backend --detach
railway domain -s backend --json

# Vercel
vercel project add rlm-lens
vercel link --project rlm-lens --yes
printf 'https://backend-production-4b1cb.up.railway.app\n' | vercel env add VITE_API_BASE production --force
printf 'https://backend-production-4b1cb.up.railway.app\n' | vercel env add VITE_API_BASE preview --force
printf 'https://backend-production-4b1cb.up.railway.app\n' | vercel env add VITE_API_BASE development --force
vercel deploy --prod --yes
```
