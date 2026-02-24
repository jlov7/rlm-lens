# RLM-Lens for Non-Technical Stakeholders

## What it is
RLM-Lens is an AI analysis product that answers questions about documents and code while showing exact evidence for each claim.

## Why it matters
- Reduces hallucination risk by forcing line-level citation.
- Helps teams audit AI answers quickly.
- Makes AI behavior explainable through an interactive trace.

## What users can do
1. Load a corpus (project docs, codebase, logs).
2. Ask a question.
3. Inspect citations and trace.
4. Export/share the run with evidence.

## Trust model in plain English
- Every answer should point to source files and line ranges.
- Users can click citations and verify context immediately.
- If evidence is weak, the UI makes that visible.

## Typical use cases
- Engineering due diligence.
- Incident response retrospectives.
- Knowledge transfer for new teams.
- Documentation audits.

## Time-to-value
With starter corpus packs, a first-time user can get a meaningful demo result in minutes.

## Deployment shape
- Frontend hosted on Vercel.
- Backend hosted on Railway.
- Data remains in backend storage under your control.

## What “good” looks like
- Fast first answer.
- Clear citations.
- Understandable trace.
- Repeatable quality checks.
