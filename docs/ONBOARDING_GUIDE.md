# Onboarding Guide

## Goal
Get from zero to first trusted answer as fast as possible.

## Path A: Fastest demo (recommended)
1. Start app with `make dev`.
2. Click `Instant demo (materialize + index)` in Step 1.
3. Wait for index completion (typically under 1 minute for fixture starter corpus).
4. Run guided prompt cards and inspect evidence.
5. Open at least one citation and one trace event before export/share.

## Path B: Your own corpus
1. Choose `Index local corpus`.
2. Set path to your project root.
3. Keep default include/exclude patterns initially.
4. Use `Balanced` preset for first run.

## Presets
- `Speed`: short budget, lower depth, quick signal.
- `Balanced`: default for most users.
- `Deep investigation`: highest coverage for difficult questions.

## Preflight checks
- API key present (`OPENAI_API_KEY`).
- Docker running (optional but recommended).
- Corpus path valid.

## First-run prompts
- Summarize architecture and cite top files.
- Locate retry policy and cite exact lines.
- Explain schema ownership with citations.

## Success criteria for onboarding
- First answer generated.
- At least one citation opened.
- Trace panel reviewed.
- Export completed.
