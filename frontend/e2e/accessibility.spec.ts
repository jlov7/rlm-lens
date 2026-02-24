import { AxeBuilder } from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

test('core app has no critical accessibility violations in deterministic mode', async ({ page }) => {
  await page.goto('/?test_mode=1&static=1&seed=21');
  await page.waitForFunction(() => window.__READY === true);

  const report = await new AxeBuilder({ page })
    .include('[data-testid="app-shell"]')
    .withTags(['wcag2a', 'wcag2aa'])
    .analyze();

  const criticalOrSerious = report.violations.filter(
    (violation) => violation.impact === 'critical' || violation.impact === 'serious'
  );
  expect(criticalOrSerious, JSON.stringify(criticalOrSerious, null, 2)).toEqual([]);
});

test('keyboard navigation works for trace timeline and evidence modal', async ({ page }) => {
  await page.goto('/?test_mode=1&static=1&seed=21');
  await page.waitForFunction(() => window.__READY === true);

  await page.getByRole('button', { name: 'Timeline' }).click();
  const timeline = page.getByLabel('Trace timeline');
  await timeline.focus();
  await page.keyboard.press('ArrowDown');
  await expect(page.getByTestId('trace-details')).toContainText('run.iteration');

  const firstCitation = page.locator('.citation-chip').first();
  await firstCitation.focus();
  await page.keyboard.press('Enter');
  await expect(page.getByTestId('evidence-modal')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByTestId('evidence-modal')).not.toBeVisible();
});
