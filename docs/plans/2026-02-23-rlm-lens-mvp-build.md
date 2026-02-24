# RLM-Lens MVP Build Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement a complete demo-ready RLM-Lens product (backend + frontend + tooling + docs) that satisfies all acceptance criteria and repo commands.

**Architecture:** Build a FastAPI backend with SQLite/FTS5 for indexing and run persistence, an RLM runtime adapter that emits trace events to JSONL+DB+SSE, and a Vite React frontend with onboarding, chat, evidence viewer, and interactive trace panel. Use deterministic fallbacks for tests while keeping real RLM integration path.

**Tech Stack:** Python 3.12 + FastAPI + pytest + ruff + mypy, Vite + React + TypeScript + Tailwind + Vitest + Playwright, Makefile + GitHub Actions.

---

### Task 1: Bootstrap repo structure and toolchains

**Files:**
- Create: `backend/pyproject.toml`, `frontend/package.json`, root `Makefile`, root `README` updates
- Create: lint/test/type configs for backend/frontend
- Create: `.github/workflows/ci.yml`

**Steps:**
1. Add backend project config/dependencies and entrypoint scaffolding.
2. Add frontend Vite/Tailwind config and app shell scaffolding.
3. Add Makefile commands `dev/check/e2e/demo/clean`.
4. Add CI workflow invoking `make check`.

### Task 2: Implement backend data model and indexing

**Files:**
- Create: `backend/src/rlm_lens/db.py`, `models.py`, `indexer.py`, `security.py`, `api/index.py`
- Test: `backend/tests/test_indexer.py`, `backend/tests/test_security.py`

**Steps:**
1. Write failing tests for file filtering, binary detection, traversal prevention.
2. Implement SQLite schema + FTS5 + corpus/file/index job persistence.
3. Implement indexing service with progress events and snapshot hash.
4. Run backend tests and iterate to green.

### Task 3: Implement runtime + tracing + runs API

**Files:**
- Create: `backend/src/rlm_lens/runtime/*.py`, `backend/src/rlm_lens/api/runs.py`
- Test: `backend/tests/test_runs.py`, `backend/tests/test_trace_logger.py`

**Steps:**
1. Write failing tests for run lifecycle, trace persistence, citation extraction.
2. Implement RLM adapter with `rlm.RLM` preferred and deterministic fallback.
3. Implement LensLogger writing JSONL and DB trace events.
4. Implement SSE stream endpoint and completion events.

### Task 4: Implement replay/export/evidence APIs

**Files:**
- Create/modify: `backend/src/rlm_lens/exporter.py`, API routes for replay/export/file slice
- Test: `backend/tests/test_export.py`

**Steps:**
1. Write failing tests for export bundle contents.
2. Implement replay endpoint cloning runtime config/messages.
3. Implement zip export with required artifacts.
4. Verify tests pass.

### Task 5: Implement frontend onboarding/workspace/trace/evidence

**Files:**
- Create: `frontend/src/*` app components and API client
- Test: `frontend/src/**/*.test.tsx`

**Steps:**
1. Build first-run onboarding flow and index progress UI.
2. Build chat workspace with citation chips and answer stream handling.
3. Build evidence modal with line highlighting and snippet copy.
4. Build trace panel graph/timeline + filters + details.

### Task 6: End-to-end verification and docs sync

**Files:**
- Create: `frontend/e2e/smoke.spec.ts`
- Modify docs to match real behavior and commands

**Steps:**
1. Implement Playwright smoke for index/query/citation/trace/export.
2. Run `make check` and `make e2e`; fix failures.
3. Update README/docs with screenshots placeholders and final instructions.
4. Record outcomes in `.codex/PLANS.md`.
