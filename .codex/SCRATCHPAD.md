## Current Task

Public readiness hardening pass: advisories, trust-boundary docs, and verification rerun.

## Status

Completed

## Plan

1. [x] Upgrade vulnerable frontend dependency chain (vite/eslint/vitest)
2. [x] Verify advisory scan is clean (`pnpm audit`)
3. [x] Tighten provider-compatibility and BYOK trust wording in public docs
4. [x] Run `make check`, `make e2e`, `make verify-visual`

## Decisions Made

- Keep key handling ephemeral: send key via run header only, avoid DB persistence.
- Explicitly document hosted trust boundary to avoid implying zero-trust transit.

## Open Questions

- None blocking.
