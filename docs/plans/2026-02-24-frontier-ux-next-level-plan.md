# Frontier UX Plan — Next Level RLM-Lens

Date: 2026-02-24
Owner: Codex
Status: Executed (2026-02-24 autonomous pass complete)

## Objective

Take RLM-Lens from strong demo quality to world-class product quality by upgrading user journeys, interaction architecture, system trust signals, and visual craft to a standard expected by top-tier UX/product review panels.

## North-Star Experience

A first-time user should:
1. Understand the product in 20 seconds.
2. Complete onboarding and run first successful query in under 3 minutes.
3. Trust the answer because evidence and trace are comprehensible by default.
4. Feel control over performance/cost/quality tradeoffs without being overwhelmed.
5. Export and share a run artifact that is review-ready for another engineer.

## Score Target

Target: 99/100 across UX criteria by finishing the full backlog below.

---

## Epic 1 — Information Architecture Rebuild

### Goal

Restructure app-level navigation and panel semantics so users always know where they are, what changed, and what to do next.

### Tasks

- [ ] Define a clear app shell hierarchy: `Command`, `Evidence`, `Trace`, `Ops`.
- [ ] Replace overloaded inline sections with explicit mode-based surfaces.
- [ ] Split primary versus advanced controls at architecture level.
- [ ] Introduce persistent context rail for run/corpus state.
- [ ] Add breadcrumb and session context across run viewer states.
- [ ] Design empty/loading/error state patterns for every major panel.
- [ ] Create “attention map” design pass (where eye should go first/second/third).

### Acceptance

- [ ] First-time users can describe layout purpose after one screen view.
- [ ] No panel combines unrelated tasks.

---

## Epic 2 — Onboarding 3.0 (Guided + Adaptive)

### Goal

Create a premium onboarding journey that adapts to user intent and shortens time-to-first-value.

### Tasks

- [ ] Add entry decision cards: `Demo`, `Index local corpus`, `Resume previous`.
- [ ] Add readiness preflight with explicit fix actions (API key, Docker, disk access).
- [ ] Add corpus health estimate before indexing (file count, size, expected duration).
- [ ] Add progressive defaults by user goal (`speed`, `balanced`, `deep investigation`).
- [ ] Add deterministic guided first prompt flow with walkthrough states.
- [ ] Add contextual teaching moments only when needed (progressive help).
- [ ] Add recoverable onboarding sessions (save/resume wizard state).
- [ ] Add post-onboarding success checkpoint and next-step CTA.

### Acceptance

- [ ] 90%+ of first-time users complete onboarding without external docs.
- [ ] First successful answer produced in <= 3 minutes on sample corpus.

---

## Epic 3 — Query Composer 2.0

### Goal

Make asking a question feel precise and powerful while reducing cognitive overhead.

### Tasks

- [ ] Introduce intent templates with richer prompt scaffolding.
- [ ] Add query linting (detect vague prompts and suggest clarifications).
- [ ] Add “quality mode” presets mapping to runtime and retrieval settings.
- [ ] Add inline budget impact estimate (speed/cost/coverage indicators).
- [ ] Add target corpus selection with clear weighting visualization.
- [ ] Add memory of recent prompt patterns per corpus.
- [ ] Add command palette for power users (`/compare`, `/evaluate`, `/watch`).
- [ ] Add keyboard-first run flow (`Cmd+Enter`, `Shift+Cmd+Enter` variants).

### Acceptance

- [ ] Composer supports basic and expert paths without visual overload.
- [ ] Users can predict tradeoffs before running.

---

## Epic 4 — Answer Experience 2.0

### Goal

Upgrade answer readability and trust framing so output is actionable, reviewable, and auditable.

### Tasks

- [ ] Replace plain markdown block with structured answer cards.
- [ ] Add explicit confidence and completeness indicators per answer section.
- [ ] Add claim-level grounding badges (grounded/weak/unsupported).
- [ ] Add “why this answer” explanation with retrieval summary.
- [ ] Add “what changed from previous run” delta summary.
- [ ] Add one-click follow-up prompts based on gaps detected.
- [ ] Add quick copy/export for summary, citations, and technical detail separately.

### Acceptance

- [ ] Engineers can scan answer quality in < 10 seconds.
- [ ] Unsupported claims are clearly visible.

---

## Epic 5 — Evidence Viewer Excellence

### Goal

Turn evidence viewing into a high-performance forensic tool, not just a modal.

### Tasks

- [ ] Add side-by-side evidence layout (answer claim vs cited source).
- [ ] Add line-range highlight persistence and deep-linking.
- [ ] Add context expansion controls (+/- lines) with keyboard shortcuts.
- [ ] Add file symbol mini-map and intra-file search.
- [ ] Add syntax/language-aware rendering polish.
- [ ] Add cross-citation navigation (`next citation`, `previous citation`).
- [ ] Add “pin evidence” workspace for comparing snippets.
- [ ] Add copy variants: raw snippet, with line refs, markdown citation block.

### Acceptance

- [ ] Citation click-to-useful-view under 150ms after data fetch.
- [ ] Users can compare at least 2 citations without losing context.

---

## Epic 6 — Trace Intelligence UX

### Goal

Make recursion trace understandable to humans at a glance and explorable at depth.

### Tasks

- [ ] Add trace narrative mode (human-readable run storyline).
- [ ] Add stage grouping (`retrieve`, `reason`, `subcall`, `finalize`).
- [ ] Add graph lane layout for deterministic readability.
- [ ] Add jump-to-error / jump-to-cost hotspots actions.
- [ ] Add time scrubber for sequence replay.
- [ ] Add trace diff mode for two runs.
- [ ] Add compact mode for large traces (clustered nodes).
- [ ] Add visual legends and persistent filter chips.
- [ ] Add performance overlays (latency/token heat).

### Acceptance

- [ ] Users can locate the causal path for a bad answer rapidly.
- [ ] Large traces remain navigable (500+ events).

---

## Epic 7 — Ops Lab Professionalization

### Goal

Elevate compare/watch/security/evals into a coherent operations workflow.

### Tasks

- [ ] Convert tabbed ops into task-oriented workflow cards.
- [ ] Add saved compare sessions with labels and notes.
- [ ] Add watcher timeline and recent auto-index events.
- [ ] Add policy findings triage states (`new`, `accepted`, `resolved`).
- [ ] Add eval suites and named benchmark presets.
- [ ] Add eval trend chart over time.
- [ ] Add one-click “promote run as baseline” for compare/eval loops.
- [ ] Add shareable ops snapshots for team review.

### Acceptance

- [ ] Ops workflows are understandable without backend knowledge.
- [ ] Compare and eval are usable for real tuning cycles.

---

## Epic 8 — Interaction and Motion Craft

### Goal

Use motion and interaction states to improve comprehension, not decoration.

### Tasks

- [ ] Define motion tokens (duration/easing/purpose).
- [ ] Add staged reveal for run lifecycle (query -> trace -> answer).
- [ ] Add subtle state transition animations for panel updates.
- [ ] Add micro-interactions for success/warning/error transitions.
- [ ] Add reduced-motion first-class behavior.
- [ ] Add deterministic static-mode safeguards for all animated states.

### Acceptance

- [ ] Motion helps users follow cause/effect across updates.
- [ ] No animation causes test nondeterminism.

---

## Epic 9 — Copywriting and Content System

### Goal

Make language precise, consistent, and confidence-building across UI.

### Tasks

- [ ] Write tone/voice standards for technical UI copy.
- [ ] Rewrite every top-level label to remove ambiguity.
- [ ] Align terminology globally (`Evidence`, `Trace`, `Run`, `Grounding`).
- [ ] Replace warning text with explicit remediation actions.
- [ ] Add contextual helper text only where confusion exists.
- [ ] Add content QA checklist for every feature PR.

### Acceptance

- [ ] No critical flow depends on guesswork from labels.
- [ ] Copy remains consistent across all panels.

---

## Epic 10 — Accessibility to AAA-Grade Practicality

### Goal

Push beyond baseline compliance to robust, engineering-grade accessibility.

### Tasks

- [ ] Add full keyboard traversal maps per screen.
- [ ] Add skip links and landmark structure audit.
- [ ] Add announced state changes for live run updates.
- [ ] Add ARIA enhancements for graph node semantics.
- [ ] Add contrast matrix tests for all tokens and states.
- [ ] Add screen-reader task-runthrough QA scripts.
- [ ] Add focus trap and return-focus audits for all overlays.

### Acceptance

- [ ] Critical and serious Axe violations remain zero.
- [ ] Core flows fully operable with keyboard and screen reader.

---

## Epic 11 — Performance and Perceived Speed

### Goal

Make the interface feel instant even with heavy data and long traces.

### Tasks

- [ ] Add interaction performance budget targets per panel.
- [ ] Instrument and optimize render hotspots in `App` and trace components.
- [ ] Introduce memoization strategy review and selective state splitting.
- [ ] Add skeleton and optimistic states for high-latency operations.
- [ ] Add virtualized render strategy for long answer/evidence/trace lists.
- [ ] Add background prefetch for likely next actions.
- [ ] Add bundle and runtime performance audit in CI.

### Acceptance

- [ ] No noticeable stutter in common flows.
- [ ] Core actions feel immediate on commodity hardware.

---

## Epic 12 — Design System and Component Governance

### Goal

Evolve ad-hoc styles into a reusable, testable design system.

### Tasks

- [ ] Extract shared primitives (button, pill, card, field, panel header).
- [ ] Define token catalog (color, type scale, spacing, radii, shadows, motion).
- [ ] Build component usage guidelines and do/don’t examples.
- [ ] Add visual regression focus stories/states for core primitives.
- [ ] Add linting rules/conventions for class naming and token usage.

### Acceptance

- [ ] New features can be built without inventing new visual patterns.
- [ ] Visual consistency holds across product surfaces.

---

## Epic 13 — Deterministic Verification 2.0

### Goal

Raise confidence from “tests pass” to “UI behavior is provably stable”.

### Tasks

- [ ] Expand visual suite to cover onboarding, workspace states, ops tabs, modal states.
- [ ] Add deterministic user-journey scripts with proof watermarks per state.
- [ ] Add geometry and overlap checks for all key panels in each viewport tier.
- [ ] Add deterministic content seeds for copy and trace payload variants.
- [ ] Add browser-specific drift budgets only when justified and documented.
- [ ] Add artifact index page for rapid human review of snapshots and diffs.

### Acceptance

- [ ] Cross-browser deterministic suite reliable and maintainable.
- [ ] Regressions are obvious and actionable from artifacts.

---

## Epic 14 — Analytics, Learning Loop, and Product Telemetry

### Goal

Close the loop between shipped UX and real usage outcomes.

### Tasks

- [ ] Define privacy-safe UX telemetry schema.
- [ ] Track onboarding drop-offs and first-run success reasons.
- [ ] Track evidence interactions (which citations are opened, pinned, exported).
- [ ] Track trace exploration behavior (filters, jumps, replay usage).
- [ ] Add UX health dashboard for product iteration.
- [ ] Add experiment framework for copy/layout variants in deterministic mode.

### Acceptance

- [ ] UX decisions become evidence-driven.
- [ ] High-impact friction points are measurable.

---

## Execution Waves

### Wave A (High leverage, 1-2 weeks)

- Epic 1, Epic 2, Epic 3, Epic 4 baseline
- Epic 9 baseline copy rewrite
- Epic 13 expanded deterministic coverage

### Wave B (Differentiation, 1-2 weeks)

- Epic 5, Epic 6, Epic 7
- Epic 8 motion craft
- Epic 11 performance optimization

### Wave C (Platform quality, 1-2 weeks)

- Epic 10 accessibility deepening
- Epic 12 design system governance
- Epic 14 telemetry and learning loop

---

## Definition of Done for “Next Level”

- [ ] UX benchmark review score >= 9/10 on clarity, trust, speed, and delight.
- [ ] Deterministic visual + geometry + accessibility suites all green.
- [ ] First-run completion and confidence metrics improved against baseline.
- [ ] Public demo script can be run without manual rescue steps.
