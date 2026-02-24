# Master prompt for Codex (one-shot)

## Recommended (use the skill)
In the Codex app, open this repository, start a new thread (Worktree mode preferred), and send:

```
$rlm-lens-builder

Build RLM-Lens end-to-end. Read AGENTS.md and all docs/*.md first, then implement the full product.
Do not stop early. Keep going until:
- make dev runs,
- make demo works,
- make check passes,
- make e2e passes,
- docs are accurate and polished.
```

## Fallback (if skills are unavailable)
Paste the following as a single prompt:

```
You are building the repository into a demo-ready product called RLM-Lens.

First read AGENTS.md and docs/PRD.md, docs/UX_SPEC.md, docs/ARCHITECTURE.md, docs/API_SPEC.md, docs/TRACE_FORMAT.md, docs/ACCEPTANCE_CHECKLIST.md.
Then implement the entire monorepo (backend + frontend + docs) per spec.

Non-negotiable outcomes:
1) Fresh clone → cp .env.example .env → set OPENAI_API_KEY → make dev works.
2) make demo indexes examples/sample_corpus and runs a guided prompt.
3) Answers include clickable citations (file + line range) that open an evidence viewer.
4) A live trace viewer shows RLM iterations/code blocks/subcalls while the run executes.
5) Runs can be replayed and exported as zip bundles (answer.md, citations.json, trace.jsonl, run.json, corpus_manifest.json).
6) make check and make e2e pass. Add CI workflow running make check.

Implementation requirements:
- Backend: Python 3.12 + FastAPI + sqlite + FTS5, package via uv.
- RLM runtime uses the rlms package (from rlm import RLM) with Docker REPL default, local fallback.
- Implement LensLogger that writes RLMLogger-compatible JSONL and streams events to UI via WS/SSE.
- Frontend: Vite React TS + Tailwind + shadcn/ui + React Flow + CodeMirror.
- UI must be intentionally designed (distinct typography, depth, tasteful motion, onboarding wizard).

Execution rules:
- Keep going until the Definition of Done is met.
- Run checks frequently and fix failures immediately.
- Use Git commits as checkpoints at major milestones.

At the end: summarize how to run it and list commands you executed.
```

