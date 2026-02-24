# Visual Verification Protocol (Deterministic)

Version: `v2`

This protocol is required before public demos or release tags.

## Purpose

Provide deterministic, repeatable UI verification that catches both visual regressions and layout integrity issues.

## Test-mode controls

RLM-Lens supports a deterministic UI mode via query params:

- `test_mode=1`: load fixture corpus/run data without backend dependence
- `seed=<int>`: controls fixture seed markers
- `static=1`: disables animation/transition/caret effects
- `ticks=<int>`: reserved deterministic timeline knob
- `debug=1`: shows debug state panel in the UI

Example URL:

```text
http://127.0.0.1:5173/?test_mode=1&seed=17&static=1&ticks=120&debug=1
```

## Readiness/debug surface

The frontend exposes:

- `window.__READY` (boolean): true when visual state is stable for capture
- `window.__RLM_LENS_DEBUG()` (function): returns machine-readable state snapshot

Visual tests must wait for `window.__READY === true` before assertions.

## Required checks

1. Screenshot assertions with Playwright `toHaveScreenshot`
   - workspace shell
   - operations deck states (`compare`, `watch`, `evals`)
   - evidence modal
2. Geometry assertions:
   - required panels exist
   - no zero-size boxes
   - no NaN/Infinity values
   - no left/center/right pane overlap
   - valid DPR
3. Focus-mode and operations panel deterministic checks
4. Cross-browser matrix:
   - Chromium
   - Firefox
   - WebKit

## Commands

Baseline/update snapshots:

```bash
cd frontend
pnpm visual:update
```

Run deterministic visual verification:

```bash
make verify-visual
```

Build artifact index:

```bash
cd frontend
pnpm visual:index
```

## Artifacts

Runtime debug artifacts are written to:

- `output/playwright/visual-debug-chromium.json`
- `output/playwright/visual-debug-firefox.json`
- `output/playwright/visual-debug-webkit.json`
- `output/playwright/visual-artifacts.md` (snapshot/debug artifact index)

Playwright stores screenshots/traces under its standard output locations.

## Gate

A public release candidate is blocked if:

- any geometry assertion fails
- any screenshot diff fails
- any browser project fails
