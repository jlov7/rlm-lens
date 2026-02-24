import { expect, test } from '@playwright/test';

test('operations deck advanced panels work in deterministic mode', async ({ page }) => {
  await page.goto('/?test_mode=1&static=1&seed=99');
  await page.waitForFunction(() => window.__READY === true);

  await expect(page.getByTestId('operations-deck')).toBeVisible();

  await page.getByRole('button', { name: 'Compare', exact: true }).click();
  await expect(page.getByTestId('compare-panel')).toBeVisible();
  await page.getByRole('button', { name: 'Compare runs' }).click();
  await expect(page.getByTestId('compare-panel').getByText(/^Overlap/i)).toBeVisible();

  await page.getByRole('button', { name: 'Watch', exact: true }).click();
  await expect(page.getByTestId('watch-panel')).toBeVisible();
  await page.getByRole('button', { name: 'Start watcher' }).click();
  await expect(page.getByText(/Status running/i)).toBeVisible();
  await page.getByRole('button', { name: 'Stop watcher' }).click();
  await expect(page.getByText(/Status stopped/i)).toBeVisible();

  await page.getByRole('button', { name: 'Security', exact: true }).click();
  await expect(page.getByTestId('security-panel')).toBeVisible();
  await page.getByRole('button', { name: 'Refresh scan' }).click();
  await expect(page.getByText(/Findings/)).toBeVisible();

  await page.getByRole('button', { name: 'Evals', exact: true }).click();
  await expect(page.getByTestId('eval-panel')).toBeVisible();
  await page.getByLabel('Eval queries').fill('where retry policy');
  await page.getByRole('button', { name: 'Run evaluation' }).click();
  await expect(page.getByText(/Latest succeeded/i)).toBeVisible();
});
