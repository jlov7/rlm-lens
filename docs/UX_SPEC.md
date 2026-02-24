# UX Spec — RLM-Lens

This spec is intentionally opinionated to achieve a *distinctive, high-end* product feel quickly.

## 1. Product design principles
1. **Trust is the feature**: every major UI element should support “why should I believe this?”
2. **Show the machine thinking**: the trace is not a log file; it’s the product’s signature.
3. **Fast path, deep path**: onboarding is simple; exploration tools are deep.
4. **Calm, not boring**: avoid “enterprise grey.” Use depth (gradients/noise), strong type, and purposeful motion.
5. **Everything is shareable**: export runs as artifacts colleagues can consume.

## 2. Visual direction (“Noir Glass + Teal Heat”)
### 2.1 Typography
- Headings: **Space Grotesk** (or similar geometric grotesk)
- Body: **Instrument Sans** (or similar)
- Monospace: **JetBrains Mono**
Avoid default “Inter everywhere.” Use 2 families max + mono.

### 2.2 Color system (tokens)
Theme: dark-forward with a warm-neutral surface option.
- Background: deep navy/charcoal gradient
- Surface: slightly lighter panels with subtle transparency (glass)
- Accent: teal/cyan spectrum + occasional warm amber for warnings
- Error: rose/red; Success: green

Define CSS variables:
- `--bg-0`, `--bg-1`, `--surface-0`, `--surface-1`
- `--text-0`, `--text-1`, `--muted`
- `--accent`, `--accent-2`
- `--warn`, `--error`, `--ok`

### 2.3 Texture & depth
- Add a subtle noise layer (CSS background image via tiny inline SVG).
- Use large, low-contrast gradient shapes in the background.
- Panels use 1px borders with alpha, plus soft shadow.

### 2.4 Motion
Use motion to improve comprehension:
- Trace nodes animate in as they arrive (scale+fade).
- Answer streaming has a gentle caret pulse.
- Side panels slide with ease; avoid bouncy over-animation.
- “Export complete” uses a celebratory micro-interaction (confetti is optional; subtle is better).

### 2.5 Iconography
Use consistent stroke icons (Lucide) + custom logo (lens mark).

## 3. Information architecture
### 3.1 Primary navigation
Single-app workspace:
- Left sidebar: **Corpora** + **Runs**
- Top bar: active corpus + budgets + connection/model status
- Main: conversation
- Right: trace / node details (dockable)

### 3.2 Core pages
1. **Welcome / Onboarding**
2. **Workspace** (default)
3. **Run viewer** (deep link to a past run)
4. **Settings** (providers, defaults, paths)

## 4. Onboarding user journey (first-run)
### 4.1 Welcome screen
- Hero copy: “Infinite context, auditable answers.”
- Two actions:
  - “Try the demo corpus”
  - “Index a folder”

### 4.2 Stepper wizard
Step 1 — Select corpus
- Choose folder picker (local path) OR choose demo corpus.
- Display file count estimate + rules summary (exclusions).

Step 2 — Provider/model
- Provider dropdown (OpenAI default)
- Model dropdown (pre-filled)
- “Connection test” button

Step 3 — Budgets
- Sliders / inputs:
  - max wall time (s)
  - max iterations
  - max depth
  - max subcalls
  - max tokens (optional)
- Show “budget bar” UI preview.

Step 4 — Index build
- Progress bar + current file
- “What’s happening?” expandable explaining index + FTS
- On completion, CTA: “Ask your first question”

### 4.3 First question guided prompt
Provide 3 big suggestion cards tailored to demo corpus:
- “Summarize the architecture and cite the top 3 files.”
- “Find the retry policy and cite exact line ranges.”
- “Identify TODOs and group by module.”

## 5. Workspace layout (desktop)
Three-pane layout:

### 5.1 Left sidebar (280px)
Tabs:
- **Runs**: list with query preview, date/time, status, cost
- **Corpus**: file tree, search box, index status
Sidebar footer: Settings + Export help

### 5.2 Center pane
Conversation timeline:
- User messages
- Assistant messages streaming
- Answer segments are structured:
  - Summary
  - Evidence-backed details (each bullet has citations)
  - “What to check next” suggestions
- Citations appear as chips like: `src/foo.py:L120-L155`

Composer:
- Multi-line input
- Attachments: optional (paste text)
- Advanced: toggles for budgets and run mode
- Primary CTA: “Run with trace”

### 5.3 Right pane (trace dock)
Two modes:
- **Graph** (default): interactive node graph
- **Timeline**: expandable list grouped by iteration

Filters:
- iteration #
- node type (metadata/iteration/code/subcall/error)
- show only errors
- show only subcalls
- search in trace text

Node details drawer:
- Code executed (monospace)
- stdout/stderr
- subcall prompt + response
- usage summary (tokens/cost/time)

## 6. Evidence viewer (signature interaction)
When user clicks a citation chip:
- Open a modal or split view with:
  - syntax highlighted file content
  - highlighted cited range
  - mini-map scrollbar
  - “Copy snippet” and “Open file” buttons
  - breadcrumb path + quick search within file
- Provide “Context expand” +/- 20 lines around citation.

## 7. Run export UX
Export is a first-class action:
- “Export run bundle” button in run header
- Modal shows what will be included
- After export:
  - show path to zip
  - show “copy share summary” (Markdown snippet)

## 8. Error states (must be delightful + actionable)
### 8.1 Missing API key
- Friendly panel with:
  - exact env var name
  - copy-to-clipboard example `.env`
  - “Retry connection test”

### 8.2 Index not built
- Disable run button and show CTA to index.

### 8.3 Budget exceeded
- Show partial results clearly labeled as partial.
- Provide next step: “Increase max wall time” or “Narrow query.”

### 8.4 Docker not available (if default sandbox uses Docker)
- Show warning toast + fallback to local sandbox
- Link to docs troubleshooting

## 9. Accessibility requirements
- All interactive elements keyboard reachable.
- Visible focus ring.
- Graph nodes have:
  - ARIA label (node type + index)
  - keyboard navigation (next/prev)
- Respect prefers-reduced-motion.
- Maintain contrast ratios for text and code blocks.

## 10. Performance requirements
- Virtualize long lists (runs list, file tree).
- Stream results via WebSocket/SSE; avoid rerender storms.
- Graph rendering must handle 500+ nodes without freezing.

## 11. Microcopy style guide
- Short, confident sentences.
- Avoid “AI disclaimers” in UI.
- Use “Evidence” and “Trace” consistently (don’t call it “logs”).

## 12. Acceptance criteria (UX)
- New user can complete onboarding without reading docs.
- Clicking citations always works and feels instantaneous (<150ms to open view after data fetched).
- Trace updates live while the run executes.
- UI looks distinctive even without custom branding: fonts + background + spacing + motion.

