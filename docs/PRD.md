# PRD — RLM-Lens

## 1. Summary
**RLM-Lens** is a local-first web app + CLI that lets users analyze *very large corpora* (codebases, docs, incident logs, policies) using **Recursive Language Models (RLMs)**. It produces:
- Evidence-backed answers with **clickable citations** (file + line ranges)
- A **live recursion trace** (iterations, code blocks, sub-calls, errors)
- Cost, token, and wall-time accounting
- Replay and export bundles for sharing inside an organization

The product is designed to be **demoable** and **trustworthy**: not just “it answers,” but “you can see *exactly how* it answered and what evidence it used.”

## 2. Problem statement
Teams increasingly want agents to work over corpora too large to fit into normal model context windows. Traditional approaches (RAG, summarization loops) often fail in one or more ways:
- missing evidence due to retrieval gaps
- “context rot” from stuffing too much into a window
- poor reproducibility / hard to debug
- answers that are hard to audit

RLMs shift the paradigm by treating long context as an **environment variable** that the model can programmatically inspect and recursively call itself over. RLM-Lens turns that capability into a usable product with **governance, observability, and UX**.

## 3. Target users & personas
### 3.1 Primary
**Staff+ engineers / tech leads**
- Need answers over a repo or large doc set
- Need confidence and citations before acting

**Security / compliance engineers**
- Need auditable “why” and evidence spans
- Need to export/share investigation artifacts

### 3.2 Secondary
**Incident commanders / SREs**
- Need to reason across long incident logs and runbooks

**Product/ops**
- Need summary with evidence over many internal docs

## 4. Goals (what success looks like)
1. **Trust**: Users can click citations and inspect evidence; they can inspect the trace to understand failure modes.
2. **Speed-to-demo**: Fresh clone → configure key → `make demo` yields a wow-worthy demo.
3. **Governed compute**: Budget caps (time/subcalls/tokens) and clear reporting of usage.
4. **Replayability**: Runs can be replayed (best effort deterministic) and exported as shareable bundles.
5. **Polish**: UI feels designed, not templated; onboarding is smooth; interactions are fast.

## 5. Non-goals (explicitly out of scope for v1)
- Multi-user auth + roles/permissions (local single-user only)
- Hosted SaaS deployment (local-first; optional docker compose is fine)
- Real-time collaboration (share bundles instead)
- Perfect determinism across model/provider changes
- Full-blown vector database integrations (optional plugin later)

## 6. Key use cases & user stories
### 6.1 “Answer with evidence”
- As a user, I index a repo and ask: “Where is the retry policy defined for service X?”
- I get an answer with citations; clicking a citation opens the exact file/lines.
- I can quickly export the run as an “evidence bundle” and share it.

### 6.2 “Debug the agent”
- As a user, I inspect the trace tree and see:
  - what searches were run
  - what files were read
  - which subcalls happened
  - where an error occurred (exceptions, timeouts)
- I can tweak budgets or query phrasing and replay.

### 6.3 “Compare two runs”
- As a user, I rerun the same question after updating the corpus index.
- I can compare the two runs’ traces and see different evidence chosen.

### 6.4 “Govern compute”
- As a user, I set a max budget (e.g., 90s, 40 subcalls).
- If exceeded, the run stops gracefully and reports partial findings + what to try.

## 7. Functional requirements

### 7.1 Indexing
- Index a folder recursively with:
  - configurable include/exclude globs
  - max file size threshold
  - binary detection and skip
  - incremental re-index (hash-based)
- Build searchable index:
  - SQLite FTS5 table for text content
  - metadata table for file paths, hashes, modified times

### 7.2 Query runtime
- Chat interface that supports:
  - system instructions
  - user messages
  - run configuration (model, budgets, sandbox)
- Use RLM to answer queries against the indexed corpus.
- Output must include:
  - answer text
  - list of citations (file + line range + snippet)
  - run summary (time, tokens/cost, subcalls)

### 7.3 Evidence / citations
- Citation format should be stable and clickable.
- Evidence spans should resolve even after reindex, via:
  - file path + line range + content hash
  - fallback: nearest matching snippet

### 7.4 Tracing & observability
- Capture full RLM trajectory:
  - metadata (run config)
  - iterations
  - code blocks executed
  - subcalls (prompt/response/usage)
  - stdout/stderr/errors
- Store traces in:
  - JSONL files (one per run)
  - SQLite DB for UI browsing and search
- Provide live streaming of events to the UI as the run executes.

### 7.5 Replay & export
- Replay a run:
  - same config, same query, same corpus snapshot (by hash)
- Export bundle (zip):
  - answer (Markdown)
  - citations (JSON)
  - trace JSONL
  - run metadata (JSON)
  - corpus snapshot manifest (file hashes, exclusions)

### 7.6 UX features
- Onboarding wizard (first run)
- Run history list with filters (by corpus, date, query)
- Trace viewer with filters (iterations/subcalls/errors)
- Evidence viewer (syntax highlight, copy, jump-to-line)

## 8. Non-functional requirements
- Local-first by default (127.0.0.1), no external data sent besides prompts to selected LLM provider.
- Performance:
  - indexing of ~10k small files should complete within minutes
  - UI should remain responsive during runs
- Reliability:
  - graceful errors with actionable messages
  - safe file access (no path traversal)
- Accessibility:
  - keyboard navigation
  - sensible focus management
  - contrast checks
- Maintainability:
  - typed code (mypy/tsc)
  - consistent formatting (ruff/prettier)
  - CI gate

## 9. Success metrics
- Time-to-first-answer on sample corpus: < 3 minutes including indexing
- Demo reliability: 3 consecutive runs without manual debugging
- Evidence quality: >90% of answers include at least 2 citations (for demo prompts)
- Crash-free dev session (no uncaught exceptions in UI)

## 10. MVP scope (must ship)
- Index folder + sample corpus
- Ask question with citations
- Live trace viewer (basic graph/timeline)
- Export bundle
- Replay run (best effort)
- Makefile workflows + tests + docs

## 11. V1 enhancements (nice-to-have)
- Run comparison UI (diff traces)
- Coverage heatmap (per file/dir)
- Pluggable vector search
- Multi-corpus workspace
- Per-run redaction settings (PII filtering)

## 12. Milestones
1. Bootstrap + CI
2. Backend indexing + API
3. RLM runtime + trace streaming
4. Frontend onboarding + workspace
5. Export/replay + demo flow
6. Hardening + documentation

