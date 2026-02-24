# Public Readiness Hardening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Status:** Completed on 2026-02-23

**Goal:** Raise RLM-Lens from MVP status to public-demo readiness by closing deterministic verification, test-depth, grounding fidelity, accessibility, and UX gaps.

**Architecture:** Add a deterministic test-mode surface in the frontend, expand backend runtime/citation and export/replay correctness tests, and formalize visual verification as a first-class release gate. Keep changes incremental to preserve existing passing pipelines while increasing confidence.

**Tech Stack:** FastAPI + sqlite/FTS5 + pytest + mypy + ruff, React + TypeScript + Vitest + Playwright, Makefile and GitHub Actions.

---

### Task 1: Deterministic visual verification protocol
Status: Complete

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/TracePanel.tsx`
- Modify: `frontend/src/styles/globals.css`
- Modify: `frontend/playwright.config.ts`
- Create: `frontend/e2e/visual.spec.ts`
- Modify: `frontend/package.json`
- Modify: `Makefile`
- Create: `docs/visual-verification-protocol.md`

**Steps:**
1. Add test-mode query controls (`test_mode`, `seed`, `static`, `ticks`, `debug`) with deterministic fixture data path.
2. Add `window.__READY` and `window.__RLM_LENS_DEBUG` surfaces in test mode.
3. Add stable data-test attributes for geometry and screenshot targeting.
4. Add Playwright visual spec with screenshot + geometry assertions and artifact outputs.
5. Add cross-browser visual project matrix and `make verify-visual` command.

### Task 2: Deep E2E smoke flow
Status: Complete

**Files:**
- Modify: `frontend/e2e/smoke.spec.ts`
- Modify: `frontend/playwright.config.ts`

**Steps:**
1. Replace minimal load-only smoke with workflow assertions.
2. Cover onboarding/index/query/citation open/trace interaction/export.
3. Ensure deterministic waiting logic and stable locators.

### Task 3: Backend grounding and runtime regression tests
Status: Complete

**Files:**
- Modify: `backend/src/rlm_lens/indexer.py`
- Modify: `backend/src/rlm_lens/runtime/runner.py`
- Create/Modify: `backend/tests/test_runtime.py`
- Create/Modify: `backend/tests/test_export.py`

**Steps:**
1. Improve citation line targeting beyond first-token heuristics.
2. Validate and clamp citation ranges against file lengths.
3. Add replay and export bundle content regression tests.
4. Add budget-exceeded behavior test.

### Task 4: Accessibility and UX hardening
Status: Complete

**Files:**
- Modify: `frontend/src/components/TracePanel.tsx`
- Modify: `frontend/src/components/EvidenceViewer.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/styles/globals.css`

**Steps:**
1. Add keyboard navigation affordances and ARIA labels in trace and modal components.
2. Improve run state/error messaging and partial budget handling in workspace.
3. Add guided prompt cards and visible budget controls in composer area.

### Task 5: Verification and rescore
Status: Complete

**Files:**
- Modify: `.codex/PLANS.md`
- Modify: `README.md`

**Steps:**
1. Run `make check`, `make e2e`, and `make verify-visual`.
2. Capture artifacts and update final score across 10 criteria.
3. Document remaining known gaps and release recommendation.
