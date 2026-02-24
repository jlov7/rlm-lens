# Release Readiness Checklist

Use this checklist before any public release tag.

Last full verification: **February 24, 2026**

## Release gates (must all pass)

1. Functional gates
- [x] `make check` passes on a clean environment.
- [x] `make e2e` passes.
- [x] `make verify-visual` passes across Chromium/Firefox/WebKit.
- [x] Demo flow executes corpus creation + indexing + run successfully (`uv run python -m rlm_lens.demo`).

2. Evidence and traceability gates
- [x] Run outputs include citations with valid line ranges.
- [x] Grounding report exists in run usage metadata.
- [x] Trace stream includes metadata + iteration telemetry and run lifecycle completion state.
- [x] Export bundle contains `answer.md`, `citations.json`, `trace.jsonl`, `run.json`, `corpus_manifest.json`.

3. Failure-mode gates
- [x] Missing API key warning path verified.
- [x] Docker unavailable fallback warning path verified.
- [x] Budget exceeded flow verified (`partial_budget_exceeded`).
- [x] Disconnect/reconnect trace flow verified.

4. Security and privacy gates
- [x] Sensitive file denylist behavior validated by tests.
- [x] Secret redaction patterns validated by tests.
- [x] Filesystem traversal protections validated by tests.

5. UX and accessibility gates
- [x] Keyboard access validated for trace timeline and evidence modal.
- [x] Focus ring visibility verified.
- [x] Axe audit shows no critical/serious violations in deterministic mode.

6. Documentation gates
- [x] README command list matches implementation.
- [x] Deployment guide validated for Vercel + Railway split.
- [x] Visual verification protocol doc is up-to-date.
- [x] Troubleshooting includes top failure modes and remediations.

7. Starter corpus and onboarding gates
- [x] Starter corpus catalog lists expected packs.
- [x] Synthetic starter corpus materialization succeeds.
- [x] First run can be completed using only starter corpus data.

## Evidence pointers

- Functional and quality gates:
  - `make check`
  - `make e2e`
  - `make verify-visual` (watermark `9:1220`)
- Demo flow:
  - `backend/src/rlm_lens/demo.py`
  - command run: `uv run python -m rlm_lens.demo`
- Trace + grounding + budget + export:
  - `backend/tests/test_runtime.py`
  - `backend/tests/test_export.py`
- Failure modes + accessibility:
  - `frontend/e2e/failure-modes.spec.ts`
  - `frontend/e2e/accessibility.spec.ts`
- Starter corpus flow:
  - `backend/tests/test_starter_corpora_api.py`
  - `frontend/src/components/Onboarding.test.tsx`
  - `make starter-corpora`
- Live deployment smoke:
  - Frontend: `https://rlm-lens.vercel.app`
  - Backend: `https://backend-production-4b1cb.up.railway.app/api/health`

## Known limitations for current release candidate

- `rlm` package integration remains best-effort due API variability across versions.
- Token/cost accounting is currently heuristic in fallback mode.
- True production-provider streaming chunks are not yet implemented; current streaming focuses on trace events.

## Sign-off template

- Release candidate commit:
- Date:
- Verified by:
- Gate results summary:
- Go/No-go decision:

## Latest sign-off (v0.1.0)

- Release candidate commit: `4064b9c`
- Date: February 24, 2026
- Verified by: Codex
- Gate results summary:
  - `make check` ✅
  - `make e2e` ✅
  - `make verify-visual` ✅ (watermark `9:1220`)
- Go/No-go decision: **Go**
