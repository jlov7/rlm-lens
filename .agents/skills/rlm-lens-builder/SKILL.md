---
name: rlm-lens-builder
description: Build the RLM-Lens product (backend + frontend + docs) end-to-end from PRD/specs with high UX polish, tests, and a demo flow. Use this when the user wants an impressive long-context RLM trace viewer app.
---

# rlm-lens-builder

## Objective
Implement **RLM-Lens** end-to-end: a local-first web app + CLI for indexing a corpus and answering questions using **Recursive Language Models** with **auditable citations** and a **live trace viewer**.

You must deliver:
- A running app (frontend+backend) with a demo dataset
- World-class docs + diagrams
- Strong verification (lint/typecheck/tests + smoke E2E)
- A polished UI/UX that is intentionally designed (not generic)

## Inputs you should expect
- This repository contains:
  - `AGENTS.md` (global instructions)
  - `docs/*` (PRD + specs)
  - `examples/sample_corpus` (demo corpus)
- User will provide (via env):
  - `OPENAI_API_KEY` (or alternative provider keys)

If anything is missing, create it (including sample corpus, .env.example, etc.).

## Non-negotiables
- Do not stop after writing scaffolding. Keep going until the app is demo-ready.
- Keep changes coherent: run checks continuously, fix failures immediately.
- Never commit secrets or private data.
- Prefer Worktree mode if available in the Codex app.

## Workflow (do these in order)

### Phase 0 — Align on scope (fast)
1. Read `docs/PRD.md`, `docs/UX_SPEC.md`, `docs/ARCHITECTURE.md`, `docs/API_SPEC.md`, `docs/TRACE_FORMAT.md`, `docs/ACCEPTANCE_CHECKLIST.md`.
2. Create a living checklist at `plans/BUILD_PLAN.md` with checkboxes for each milestone.
3. Start implementation immediately; do not ask the user questions unless blocked.

### Phase 1 — Bootstrap repo
Create the target monorepo structure and tooling:
- Root `Makefile` with: `dev`, `check`, `e2e`, `demo`, `clean`
- Backend uses `uv` + python 3.12
- Frontend uses `pnpm` + Vite React TS
- Add `.env.example`, `.gitignore`, `LICENSE` (MIT by default)
- Add CI workflow (GitHub Actions) that runs `make check` and (optional) `make e2e` on push/PR

Checkpoint commit: `chore: bootstrap repo`

### Phase 2 — Backend MVP
Implement FastAPI backend:
- Corpus indexing with SQLite FTS5
- File reading utilities with safe path handling + allowlist/denylist
- Run storage (sqlite) for runs, traces, citations
- RLM runtime:
  - use `rlms` package (`from rlm import RLM`)
  - default to Docker REPL environment when available
  - implement a **LensLogger** that:
    - writes JSONL per run compatible with `RLMLogger` format
    - streams events to the frontend via WebSocket/SSE
- API endpoints per `docs/API_SPEC.md`
- Add pytest tests

Checkpoint commit: `feat: backend mvp`

### Phase 3 — Frontend MVP (high polish)
Implement the frontend:
- Beautiful onboarding wizard:
  1) choose folder / corpus
  2) select provider/model
  3) set budgets
  4) build index (show progress)
- Main workspace:
  - Chat composer + streaming answer
  - Evidence chips that open the cited span in an evidence viewer
  - Trace panel: interactive graph + node details
  - Run list (history), replay, export
- Design requirements:
  - Bold typography, clear visual direction, CSS variables, subtle background treatment
  - Meaningful motion: transitions help comprehension (trace node reveal, answer streaming, panel open)
  - Accessibility: keyboard nav, focus rings, ARIA, contrast

Checkpoint commit: `feat: ui mvp`

### Phase 4 — Demo readiness
- Provide `examples/sample_corpus` and a scripted demo prompt sequence
- Implement `make demo` to:
  - create an index for sample corpus
  - start backend+frontend
  - open the browser (best effort) or print URL
- Add at least one end-to-end Playwright test:
  - index sample corpus
  - run a query
  - assert citations appear
  - open trace node details

Checkpoint commit: `feat: demo + e2e smoke`

### Phase 5 — Documentation & diagrams
- World-class README:
  - What is RLM-Lens + why it’s different
  - Architecture diagram
  - Quickstart
  - Demo script
  - Screenshots placeholders
- Ensure `docs/*` are accurate and match implementation.
- Include diagrams (Mermaid + exported SVGs in `assets/diagrams/`).

Checkpoint commit: `docs: polish`

### Phase 6 — Hardening pass
- Run `make clean && make check && make e2e` from a clean environment (best effort)
- Fix all issues found
- Ensure `make dev` is stable and logs are readable
- Ensure export bundles are correct and replay works

Final checkpoint commit: `chore: hardening`

## Output format at the end of the run
When you are finished, summarize:
- How to run (`make dev`, `make demo`)
- Where config lives
- What was implemented (features checklist)
- Known limitations (if any) + next steps
- Verification evidence (commands run + results)

## If you get stuck
- Prefer making a reasonable assumption + proceeding.
- If blocked by a missing dependency, add detection + fallback paths.
- If Docker isn’t available, auto-fallback to local REPL with a visible warning in UI.

