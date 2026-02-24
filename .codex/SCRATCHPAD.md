## Current Task

Multi-provider runtime expansion + secure hosted BYOK flow for Vercel/Railway demos.

## Status

Completed

## Plan

1. [x] Add failing tests for provider diagnostics/contracts (backend + frontend)
2. [x] Implement backend provider catalog + adapter key requirements
3. [x] Implement per-run secure provider key header handling (not persisted)
4. [x] Expand frontend provider UX and add session key vault
5. [x] Update docs/env/deployment guidance
6. [x] Run `make check`, `make e2e`, `make verify-visual`

## Decisions Made

- Keep key handling ephemeral: send key via run header only, avoid DB persistence.
- Use a curated provider list (frontier labs + key OpenAI-compatible gateways).

## Open Questions

- None blocking.
