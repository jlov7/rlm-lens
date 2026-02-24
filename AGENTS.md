# RLM-Lens — Agent Instructions (AGENTS.md)

This repository is intended to be built autonomously by a coding agent (Codex) into a polished, demo-ready product.

## Mission
Build **RLM-Lens**: a local-first web app + CLI that lets a user index a large corpus (docs/code/logs) and ask questions using **Recursive Language Models (RLMs)**, producing:
- Evidence-backed answers with **clickable citations**
- A **live recursion/trajectory trace** (tree / timeline)
- Cost + token + time accounting
- Replay/export of runs for internal sharing

The product must be impressive in a demo: modern UI, smooth onboarding, rich trace visualization, and reliable local setup.

## North-star outcomes (non-negotiable)
1. **It runs cleanly from zero**: a new user can go from clone → `make dev` → browse UI in under 5 minutes.
2. **No broken workflows**: lint, typecheck, unit tests, and a minimal E2E smoke test must pass.
3. **Auditable answers**: every answer must include citations that map to file+line ranges.
4. **Traceability**: every run has a saved trace, viewable in the UI, and exportable as a share bundle.
5. **Delightful UI**: bold, intentional visual design (not template-looking) + accessibility + responsive.

## Recommended stack (use unless strongly justified otherwise)
- Backend: **Python 3.12**, **FastAPI**, **uvicorn**, **pydantic**
- Packaging: `uv` for Python deps; `pnpm` for frontend deps
- DB: `sqlite` (SQLModel or sqlite3) + SQLite **FTS5** for BM25-ish search
- Frontend: **Vite + React + TypeScript**, TailwindCSS, shadcn/ui (Radix), React Flow (trace graph), CodeMirror (evidence viewer)
- Tests:
  - backend: pytest
  - frontend: vitest + react-testing-library
  - e2e: playwright (smoke only)

## RLM integration requirement
Use the official `rlms` PyPI package (Recursive Language Models library).
- Prefer an **isolated** environment for the RLM REPL by default (Docker REPL) with a fallback to local REPL.
- Use a logger that emits JSONL trajectory (and also streams events to the UI).

## Repo layout (target)
- `backend/` FastAPI app, indexing, RLM runtime, trace store
- `frontend/` React app
- `docs/` product + engineering docs
- `.agents/skills/` builder skill for Codex
- `Makefile` at repo root for one-command workflows

## Work style / execution rules
- Act like a senior engineer: implement end-to-end, not partial.
- Use Git checkpoints:
  - `chore: bootstrap repo`
  - `feat: indexing`
  - `feat: rlm runtime + tracing`
  - `feat: ui`
  - `docs: polished docs`
- If using Codex app, prefer **Worktree mode** for safety.
- Avoid long preambles; keep momentum until the deliverable is complete.
- When searching repo content, prefer `rg` and `rg --files`.
- Never commit secrets. Use `.env.example` and documented environment variables.

## Commands (must exist)
- `make dev` — run backend + frontend in dev mode
- `make check` — format, lint, typecheck, tests (backend + frontend)
- `make e2e` — run Playwright smoke
- `make demo` — index `./examples/sample_corpus` and open UI with a preloaded demo prompt
- `make clean` — remove caches, build artifacts

## Quality bar for UI (explicit)
Avoid generic dashboards. Requirements:
- Custom typography (not default stacks).
- Clear, consistent design tokens (CSS variables) and a distinctive visual direction.
- A real onboarding flow with a guided first-run.
- Meaningful motion (a few animations that aid comprehension).
- Evidence viewer must feel excellent: quick open, syntax highlight, jump-to-line, copy snippet.
- Trace viewer must be interactive: zoom/pan, node details panel, filters (iterations/subcalls/errors).
- Accessibility: keyboard navigation, focus rings, contrast, ARIA on interactive graph nodes.

## Documentation (must be written)
- README with screenshots section (placeholders OK), architecture diagram, quickstart
- docs: PRD, architecture, API spec, trace schema, troubleshooting, runbook, evaluation plan

## Definition of Done
- `make check` passes on a clean machine
- `make dev` brings up UI + backend with no manual steps besides env vars
- Demo flow works:
  1) index sample corpus
  2) ask question
  3) see evidence + trace
  4) export run bundle
