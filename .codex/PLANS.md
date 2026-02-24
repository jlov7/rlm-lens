## Purpose / Big Picture

Deliver a world-class, public-ready RLM-Lens release with a rigorous, panel-grade score across 10 criteria (target: as close to 100/100 as currently feasible), including deterministic visual verification and end-to-end product reliability.

Why this matters:
- The product is about to be made public.
- The current state has partial advanced feature integration and hidden regressions.
- We need one exhaustive source of truth for execution and completion evidence.

## Success Criteria (Hard Gates)

1. `make check` passes on clean run.
2. `make e2e` passes.
3. `make verify-visual` passes with deterministic artifacts.
4. `make demo` works from zero-like state.
5. No broken core workflows: onboarding, index, run, trace stream/reconnect, evidence open, replay, export.
6. New advanced capabilities are fully wired backend+frontend+tests+docs.

## 10-Criterion Score Framework (Target)

1. Product reliability and setup ergonomics
2. Retrieval and answer quality controls
3. Citation fidelity and evidence UX
4. Trace/observability depth
5. Frontend UX/UI quality and originality
6. Accessibility and keyboard behavior
7. Security/privacy posture and policy visibility
8. Advanced operational tooling (watchers, evaluations, compare)
9. Test/verification rigor
10. Documentation/release readiness

## Progress

- [x] Audit existing implementation and identify integration drift
- [x] Establish exhaustive execution plan and tracking artifacts
- [x] Phase 1: Stabilize and complete backend advanced features
- [x] Phase 2: Implement world-class frontend advanced UX surfaces
- [x] Phase 3: Expand deterministic verification + tests
- [x] Phase 4: Polish docs and scorecard with concrete evidence
- [x] Phase 5: Run all quality gates and fix until fully green

## Exhaustive Task Checklist

### Phase 1 — Backend completion

- [x] Fix `runtime/runner.py` syntax + lint issues and ensure runtime retrieval config works.
- [x] Extend runtime config schema (`models.py`) for advanced knobs:
  - [x] `performance_mode`
  - [x] `target_corpora`
  - [x] retrieval weight block
  - [x] `corpus_weights`
- [x] Ensure run and citation APIs return `corpus_id` in citation objects.
- [x] Wire `Services` to include:
  - [x] `WatchManager`
  - [x] `PolicyEngine`
  - [x] `EvaluationEngine`
- [x] Add router endpoints for comparison:
  - [x] `POST /api/runs/compare`
  - [x] `GET /api/runs/compare/{compare_id}`
- [x] Add router endpoints for step-level trace/debug:
  - [x] `GET /api/runs/{run_id}/trace/summary`
  - [x] `GET /api/runs/{run_id}/trace/step`
- [x] Add watcher API endpoints:
  - [x] `POST /api/corpora/{corpus_id}/watch/start`
  - [x] `POST /api/corpora/{corpus_id}/watch/stop`
  - [x] `GET /api/corpora/{corpus_id}/watch`
  - [x] `GET /api/watchers`
- [x] Add policy/security endpoints:
  - [x] `GET /api/corpora/{corpus_id}/policy/summary`
  - [x] `GET /api/corpora/{corpus_id}/policy/findings`
- [x] Add evaluation endpoints:
  - [x] `POST /api/evals`
  - [x] `GET /api/evals`
  - [x] `GET /api/evals/{eval_id}`
- [x] Add export share-view endpoint:
  - [x] `GET /api/runs/{run_id}/share`
- [x] Harden backend typing, validation, and error handling for new endpoints.
- [x] Add/extend backend tests for all new capabilities.

### Phase 2 — Frontend advanced UX surfaces

- [x] Extend `frontend/src/lib/types.ts` with new API types.
- [x] Extend `frontend/src/lib/api.ts` with new endpoint clients.
- [x] Upgrade main app UX to include advanced panels:
  - [x] Compare runs workflow
  - [x] Watcher controls and live status
  - [x] Security/policy findings dashboard
  - [x] Eval runner and results board
  - [x] Retrieval tuning controls (weights/top-k/targets)
- [x] Improve trace UX:
  - [x] step detail drilldown
  - [x] retrieval diagnostics panel
  - [x] better status/telemetry framing
- [x] Ensure responsive behavior for new surfaces desktop+mobile.
- [x] Preserve existing deterministic test mode compatibility.
- [x] Keep accessibility semantics for all new controls.

### Phase 3 — Deterministic verification and tests

- [x] Add backend unit tests for:
  - [x] watchers lifecycle
  - [x] policy summary/findings endpoints
  - [x] eval lifecycle
  - [x] run compare endpoint
  - [x] trace summary/step endpoints
- [x] Add frontend unit tests for new controls/state transitions.
- [x] Add/extend Playwright tests for:
  - [x] compare workflow in test mode
  - [x] security/eval/watch panels visibility and controls
  - [x] deterministic visual captures for new states
- [x] Rebaseline visual snapshots only if required after intentional UI changes.

### Phase 4 — Documentation and release readiness

- [x] Update `docs/API_SPEC.md` with all new endpoints and payloads.
- [x] Update `docs/ARCHITECTURE.md` for new backend components and data flows.
- [x] Add/refresh runbook entries for watchers, policy scan, and evals.
- [x] Update quality scorecard with evidence-based scoring and residual gaps.

### Phase 5 — Final gates

- [x] Run `make check` and resolve all failures.
- [x] Run `make e2e` and resolve all failures.
- [x] Run `make verify-visual` and resolve all failures.
- [x] Run `make demo` and verify full flow.
- [x] Final pass: quick regression walkthrough against all major workflows.

## Surprises & Discoveries

- Date: 2026-02-24
  Discovery: Advanced backend modules (retrieval/policy/watch/eval) exist but API/model/frontend wiring is incomplete.
  Impact: High; integration gaps create product-quality mismatch and hidden failure risk.

- Date: 2026-02-24
  Discovery: `runtime/runner.py` includes escaped quote syntax corruption in `_compose_answer`.
  Impact: Critical; backend checks fail immediately.

- Date: 2026-02-24
  Discovery: New operations panels changed deterministic workspace screenshot height in all browsers.
  Impact: Medium; required visual snapshot rebaseline and rerun of cross-browser visual verification.

## Decision Log

- Date: 2026-02-24
  Decision: Prioritize backend stabilization and complete API contracts before additional frontend polish.
  Rationale: Prevents UI-on-broken-contract regressions and accelerates deterministic verification.
  Alternatives considered: frontend-first polish pass.

- Date: 2026-02-24
  Decision: Keep advanced feature set focused on operationally useful capabilities already scaffolded in code (watchers/policy/evals/hybrid controls/compare).
  Rationale: Maximizes completion confidence tonight while still delivering substantial next-level functionality.
  Alternatives considered: introducing net-new speculative architecture.

## Outcomes & Retrospective

Completed:
- Backend advanced capabilities fully integrated (compare/watch/policy/evals/share/trace-summary-step).
- Frontend advanced operations deck shipped with compare/watch/security/eval workflows.
- Retrieval tuning controls and performance mode exposed in composer and runtime payload.
- Docs updated (API spec, architecture, runbook, scorecard, execution plan).
- Verification gates executed and green:
  - `make check`
  - `make e2e`
  - `make verify-visual`
  - `make demo` flow validated through index + run + evidence output (command kept server processes alive after readiness as expected).

Residual gaps:
- Provider-native token/cost accounting remains a future enhancement.
- Large-corpus sustained benchmark automation remains a future enhancement.

## Next-Level Planning (2026-02-24 follow-up)

Exhaustive frontier UX backlog created for ambitious next-stage execution:
- `docs/plans/2026-02-24-frontier-ux-next-level-plan.md`

This backlog defines 14 epics and wave-based execution to move from current strong state to panel-grade world-class product experience.

## Frontier UX Execution Pass (2026-02-24, Autonomous)

Status: In Progress

Execution tracker:
- `docs/plans/2026-02-24-frontier-ux-execution-log.md`

Active objective:
- Complete Wave 1 through Wave 4 tasks from the frontier backlog and close with full quality gates.

Hard completion evidence required before closeout:
- `make check`
- `make e2e`
- `make verify-visual`

### Frontier UX Execution Pass Outcome

Status: Completed

Evidence:
- Tracker completed: `docs/plans/2026-02-24-frontier-ux-execution-log.md`
- Quality gates green in final state:
  - `make check`
  - `make e2e`
  - `make verify-visual` (cross-browser `VISUAL_PASS`, watermark `9:1220`)

## Public Release Productization Pass (2026-02-24)

Status: Completed
Tracker: `docs/plans/2026-02-24-public-release-productization-pass.md`

Delivered:
- Starter corpus onboarding system (catalog/materialize APIs + frontend integration)
- Deployment-ready split architecture assets (Vercel frontend + Railway backend)
- World-class docs pass (README + non-technical/onboarding/user/deployment guides)
- Showboat showcase artifact with screenshots and verification evidence

Final gates:
- `make check` ✅
- `make e2e` ✅
- `make verify-visual` ✅ (`watermark=9:1220`)

## Final Polish And Release Closure (2026-02-24)

Status: Completed
Tracker: `docs/plans/2026-02-24-final-polish-and-release-closure.md`

Objective:
- Eliminate remaining first-run friction and fully close release evidence for public launch.

Outcome:
- Instant demo onboarding shipped (materialize + index + handoff).
- Workspace shortcut/help modal shipped with keyboard toggle.
- `make starter-corpora` fixed and validated.
- Live deployments validated:
  - Railway backend `https://backend-production-4b1cb.up.railway.app`
  - Vercel frontend `https://rlm-lens.vercel.app`
- Final gates green:
  - `make check`
  - `make e2e`
  - `make verify-visual` (`watermark=9:1220`)

## Multi-Provider + Secure BYOK Expansion (2026-02-24)

Status: Completed
Tracker: `docs/plans/2026-02-24-multi-provider-byok-world-class.md`

Objective:
- Add production-grade multi-provider ergonomics and secure hosted BYOK handling for demo/public usage.

Execution checklist:
- [x] Introduce backend provider catalog and diagnostics metadata for key presence across providers.
- [x] Extend runtime adapter/provider validation beyond OpenAI-only assumptions.
- [x] Add non-persistent per-run provider key flow via request headers.
- [x] Ship frontend provider selector/model presets and session-only key vault UX.
- [x] Update docs: README, security/privacy, deployment guide, API spec, env vars.
- [x] Run full quality gates (`make check`, `make e2e`, `make verify-visual`) and resolve failures.
