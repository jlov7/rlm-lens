# Contributing to RLM-Lens

## Repo commands
- `make dev` — run dev servers
- `make check` — lint/type/test
- `make e2e` — Playwright smoke
- `make verify-visual` — deterministic cross-browser visual suite
- `make demo` — demo flow

## Code style
Backend:
- Python 3.12
- ruff (lint + format)
- mypy for types
- pytest for tests

Frontend:
- TypeScript strict
- eslint + prettier
- Tailwind + shadcn/ui components

## Pull requests
- Keep PRs focused.
- Add tests for behavior changes.
- Include screenshots for UI changes.

## Security
- Never commit secrets.
- Avoid logging sensitive data; redact.
