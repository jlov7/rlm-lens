# Acceptance Checklist — RLM-Lens

## A. Setup
- [ ] Fresh clone → `make dev` works
- [ ] `.env.example` documents required env vars
- [ ] UI loads and shows onboarding

## B. Indexing
- [ ] Can index `examples/sample_corpus`
- [ ] Shows progress updates (SSE/WS)
- [ ] Index result summary includes:
  - files indexed
  - files skipped + reasons
- [ ] Incremental reindex works (modify a file, reindex updates)

## C. Query + citations
- [ ] Can run query and see streaming answer
- [ ] Answer includes >= 2 citations for demo prompts
- [ ] Clicking citation opens evidence viewer
- [ ] Evidence viewer shows correct file/lines and highlights range

## D. Trace viewer
- [ ] Trace updates live during run
- [ ] Graph nodes are interactive (click selects)
- [ ] Node details show code + stdout/stderr + subcall info
- [ ] Filters work (errors only, subcalls only)

## E. Budgets
- [ ] Budget settings visible and editable
- [ ] Set `max_wall_time_s=1` causes graceful partial completion with status
- [ ] UI explains budget exceed and suggests remediation

## F. Replay + export
- [ ] Replay creates a new run
- [ ] Export creates a zip bundle
- [ ] Bundle includes:
  - answer.md
  - citations.json
  - trace.jsonl
  - run.json
  - corpus_manifest.json
- [ ] Export UI provides path and a copyable share summary

## G. Verification
- [ ] `make check` passes (backend + frontend)
- [ ] `make e2e` passes
- [ ] CI workflow exists and runs checks

## H. Docs
- [ ] README explains what this is and why it’s impressive
- [ ] Architecture diagram included
- [ ] Troubleshooting covers top failure modes

