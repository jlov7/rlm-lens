# Public Release Productization Pass

Date: 2026-02-24
Status: Completed
Owner: Codex

## Goal
Make RLM-Lens publication-ready with starter data onboarding, deployment-ready infrastructure split (Vercel + Railway), world-class documentation, and demo/showcase assets.

## Execution Checklist

### 1) Starter corpus experience
- [x] Backend starter corpus catalog + materialization service
- [x] API endpoints:
  - [x] `GET /api/starter-corpora`
  - [x] `POST /api/starter-corpora/{pack_id}/materialize`
- [x] Starter corpus CLI helper
- [x] `make starter-corpora` command
- [x] Onboarding UI integration for one-click pack setup
- [x] Backend tests for starter corpus APIs

### 2) Deployment hardening
- [x] Configurable CORS via env (`RLM_LENS_CORS_ORIGINS`)
- [x] Configurable data dir via env (`RLM_LENS_DATA_DIR`)
- [x] Railway deployment config (`railway.json`)
- [x] Backend production container (`backend/Dockerfile`)
- [x] Vercel frontend config (`vercel.json`)
- [x] Production frontend env template (`frontend/.env.production.example`)

### 3) Documentation uplift
- [x] README rewrite with ASCII logo, screenshots, architecture Mermaid, quickstart/deploy instructions, and disclaimer
- [x] Non-technical overview doc
- [x] Onboarding guide
- [x] User guide
- [x] Vercel+Railway deployment guide
- [x] Architecture/API/runbook/troubleshooting/release-readiness updates

### 4) Showcase assets
- [x] Curated screenshot set under `assets/screenshots/`
- [x] Showboat release showcase document with evidence and images

### 5) Verification
- [x] `make check`
- [x] `make e2e`
- [x] `make verify-visual`

## Verification evidence
- Deterministic visual watermark: `9:1220` on Chromium/Firefox/WebKit.
- Visual artifact index generated at `output/playwright/visual-artifacts.md`.

## Key files touched
- Backend: `starter_corpora.py`, `starter_corpora_cli.py`, `services.py`, `router.py`, `config.py`, `main.py`, `tests/test_starter_corpora_api.py`
- Frontend: onboarding integration + API/types
- Deployment: `railway.json`, `vercel.json`, `backend/Dockerfile`, env examples
- Docs: README + new/updated guides and plans
