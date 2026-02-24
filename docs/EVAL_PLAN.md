# Evaluation Plan — RLM-Lens

This plan focuses on **reliability**, **trace correctness**, and **demo quality**.

## 1. Evaluation dimensions
1. **Correctness**: Does the answer match evidence in the corpus?
2. **Grounding**: Are citations valid, clickable, and aligned to answer claims?
3. **Trace fidelity**: Does the trace reflect the actual recursive process and subcalls?
4. **Budget behavior**: Does the system stop gracefully when budgets are exceeded?
5. **UX quality**: Can a new user complete the flow without docs?

## 2. Automated checks (must be in CI)
### 2.1 Backend
- Unit tests:
  - indexer file filtering, hashing, binary detection
  - FTS search ranking basic sanity
  - path traversal prevention
  - trace JSONL writer schema validity
- Integration tests:
  - create corpus → index → run query (mock provider if possible)
  - export bundle contains expected files
- Typechecking:
  - mypy strict-ish

### 2.2 Frontend
- Typechecking: `tsc --noEmit`
- Unit tests:
  - citation chip click opens evidence viewer
  - trace node selection updates details panel
- Lint/format: eslint/prettier

### 2.3 E2E (Playwright, smoke only)
Scenario:
1. Launch app (dev or preview)
2. Choose demo corpus
3. Build index
4. Run demo query
5. Assert citations exist
6. Open trace panel and click a node
7. Export bundle and assert success toast

## 3. Golden demo prompts (ship in repo)
Provide at least 5 prompts in `examples/demo_prompts.md`:
1. “Summarize the architecture and cite the 3 most important files.”
2. “Find the retry policy and cite exact line ranges.”
3. “List TODOs and group by module.”
4. “Where is the database schema defined? Cite it.”
5. “What are the main API endpoints? Cite the router definitions.”

## 4. Manual evaluation checklist
- Fresh clone: follow README quickstart.
- Onboarding wizard:
  - never dead-ends
  - connection test works
  - index progress updates
- Workspace:
  - answer streams
  - citations open correct file slice
  - trace tree updates live
- Export:
  - zip opens
  - includes answer.md, citations.json, trace.jsonl, manifest.json
- Replay:
  - run is created and completes
- Budget exceed:
  - set max_wall_time_s = 1
  - ensure partial run ends gracefully with “budget exceeded” status

## 5. Metrics captured per run
- wall time
- total subcalls
- total input/output tokens (if provider reports)
- cost estimate (if provider reports)
- number of citations
- number of unique files cited
- trace node count

## 6. Benchmark harness (optional)
A simple harness script can run golden prompts and record:
- success/failure
- runtime
- citations count
- budget usage

Output to `./.rlm-lens/evals/YYYY-MM-DD.json`.

