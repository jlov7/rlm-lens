# Multi-Provider + Secure BYOK World-Class Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add robust multi-provider support ergonomics and a secure hosted BYOK flow (non-persistent keys) for public demos on Vercel + Railway.

**Architecture:** Introduce a backend provider catalog that centralizes provider metadata and key requirements, expose that metadata through diagnostics, and wire runtime adapter warnings/key checks against the selected provider. Add an optional per-run provider key header path so user keys are never persisted in DB. Update frontend onboarding/runtime UX to select providers, show key readiness, and submit session-only keys on run requests.

**Tech Stack:** FastAPI + pydantic + pytest (backend), React + TypeScript + vitest (frontend), Playwright smoke/visual verification.

---

## Progress

- [x] Task 1: Add failing tests for provider catalog and diagnostics payload
- [x] Task 2: Add failing tests for adapter/provider key requirements and runtime header handling
- [x] Task 3: Implement backend provider catalog module and diagnostics integration
- [x] Task 4: Implement secure per-run provider key header flow (no persistence)
- [x] Task 5: Implement frontend provider UX updates and session key vault flow
- [x] Task 6: Update docs and env examples
- [x] Task 7: Run all quality gates and capture final evidence

## Surprises & Discoveries

- Visual baselines needed re-generation after adding provider/session-key controls because workspace height changed across all browsers.
- Existing `request()` merge logic in frontend dropped `Content-Type` whenever custom headers were passed; fixed while implementing BYOK run header.

## Decision Log

- Use curated provider support list now (OpenAI, Anthropic, Gemini, xAI, OpenRouter, Together, Groq, Fireworks) rather than attempting every possible API gateway in one pass.
- Keep BYOK flow ephemeral via `X-RLM-LENS-PROVIDER-KEY` per-run header; do not persist keys in DB or runtime config.
- Keep runtime execution `rlm`-first and fallback-safe; provider UI/diagnostics are production-ready while backend-specific deep integrations can be layered later.

## Validation Gates

1. `make check`
2. `make e2e`
3. `make verify-visual`

## Outcomes & Retrospective

- Backend now exposes provider diagnostics with key readiness by provider and supported BYOK header metadata.
- Runtime adapter now validates key requirements per provider and supports ephemeral per-run key injection path.
- Frontend now provides provider/model controls and a session API key vault input (memory-only behavior explained in UI).
- Docs and deployment guidance now explain multi-provider setup and hosted BYOK trust model.
- Validation complete:
  - `make check` ✅
  - `make e2e` ✅
  - `make verify-visual` ✅ (`VISUAL_PASS` chromium/firefox/webkit, watermark `9:1220`)
