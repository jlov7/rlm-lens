import { expect, test } from '@playwright/test';
import fs from 'node:fs/promises';
import path from 'node:path';

test('deterministic workspace visual baseline', async ({ page, browserName }) => {
  await page.goto('/?test_mode=1&seed=17&static=1&ticks=120&debug=1', { waitUntil: 'networkidle' });
  await page.waitForFunction(() => window.__READY === true);

  const geometry = await page.evaluate(() => {
    const targets = [
      '[data-testid="workspace-grid"]',
      '[data-testid="left-rail"]',
      '[data-testid="center-pane"]',
      '[data-testid="trace-panel"]',
      '[data-testid="answer-panel"]',
      '[data-testid="trace-details"]',
      '[data-testid="operations-deck"]',
      '#command-panel',
      '#ops-panel',
    ];

    const failures: string[] = [];
    const boxes: Record<string, { x: number; y: number; width: number; height: number }> = {};

    for (const selector of targets) {
      const el = document.querySelector(selector) as HTMLElement | null;
      if (!el) {
        failures.push(`Missing selector ${selector}`);
        continue;
      }
      const rect = el.getBoundingClientRect();
      if (!Number.isFinite(rect.x) || !Number.isFinite(rect.y) || !Number.isFinite(rect.width) || !Number.isFinite(rect.height)) {
        failures.push(`Non-finite rect for ${selector}`);
      }
      if (rect.width <= 0 || rect.height <= 0) {
        failures.push(`Zero-sized rect for ${selector}`);
      }
      boxes[selector] = {
        x: rect.x,
        y: rect.y,
        width: rect.width,
        height: rect.height,
      };
    }

    const left = boxes['[data-testid="left-rail"]'];
    const center = boxes['[data-testid="center-pane"]'];
    const trace = boxes['[data-testid="trace-panel"]'];

    if (left && center && left.x + left.width > center.x + 1) {
      failures.push('Left rail overlaps center pane');
    }
    if (center && trace && center.x + center.width > trace.x + 1) {
      failures.push('Center pane overlaps trace pane');
    }

    const dpr = window.devicePixelRatio;
    if (!Number.isFinite(dpr) || dpr <= 0) {
      failures.push('Invalid devicePixelRatio');
    }

    return {
      failures,
      boxes,
      dpr,
      watermark: `${targets.length}:${Math.round((left?.width ?? 0) + (center?.width ?? 0) + (trace?.width ?? 0))}`,
    };
  });

  expect(geometry.failures, `Geometry failures: ${geometry.failures.join(', ')}`).toEqual([]);

  const debugState = await page.evaluate(() => window.__RLM_LENS_DEBUG?.() ?? null);
  const artifactDir = path.resolve(process.cwd(), '..', 'output', 'playwright');
  await fs.mkdir(artifactDir, { recursive: true });
  await fs.writeFile(
    path.join(artifactDir, `visual-debug-${browserName}.json`),
    JSON.stringify({ browserName, geometry, debugState }, null, 2),
    'utf-8'
  );

  await expect(page.locator('[data-testid="app-shell"]')).toHaveScreenshot('workspace.png', {
    animations: 'disabled',
  });

  await page.getByRole('button', { name: 'Ops' }).click();
  await page.getByRole('button', { name: 'Compare', exact: true }).click();
  await expect(page.locator('[data-testid="operations-deck"]')).toHaveScreenshot('ops-compare.png', {
    animations: 'disabled',
  });
  await page.getByRole('button', { name: 'Watch', exact: true }).click();
  await expect(page.locator('[data-testid="operations-deck"]')).toHaveScreenshot('ops-watch.png', {
    animations: 'disabled',
  });
  await page.getByRole('button', { name: 'Evals', exact: true }).click();
  await expect(page.locator('[data-testid="operations-deck"]')).toHaveScreenshot('ops-evals.png', {
    animations: 'disabled',
  });

  await page.getByRole('button', { name: /src\/retry_policy\.py:L12-L28/i }).click();
  await expect(page.locator('[data-testid="evidence-modal"]')).toBeVisible();
  await expect(page.locator('[data-testid="evidence-modal"]')).toHaveScreenshot('evidence-modal.png', {
    animations: 'disabled',
  });

  console.log(`VISUAL_PASS ${browserName} watermark=${geometry.watermark}`);
});
