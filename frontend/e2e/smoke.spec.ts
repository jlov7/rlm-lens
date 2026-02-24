import { expect, test } from '@playwright/test';

test('core workflow smoke', async ({ page }) => {
  await page.goto('/');

  const onboardingTitle = page.getByText('Infinite context, auditable answers.');
  if (await onboardingTitle.isVisible().catch(() => false)) {
    await expect(onboardingTitle).toBeVisible();
    await page.getByRole('button', { name: 'Continue' }).click();
    await page.getByRole('button', { name: 'Continue' }).click();
    await page.getByRole('button', { name: 'Continue' }).click();
    await page.getByRole('button', { name: /Start indexing/i }).click();
    await Promise.race([
      page.getByText('Index complete. Ready to ask your first question.').waitFor({ state: 'visible', timeout: 60_000 }),
      page.getByRole('button', { name: 'Run with trace' }).waitFor({ state: 'visible', timeout: 60_000 }),
    ]);
  }

  await expect(page.getByRole('button', { name: 'Run with trace' })).toBeVisible();
  const questionBox = page.getByLabel('Question input');
  await questionBox.fill('Find the retry policy and cite exact line ranges.');

  await page.getByRole('button', { name: /Run with trace/i }).click();

  await expect(page.getByTestId('answer-panel')).toContainText('Summary', { timeout: 30_000 });
  const firstCitation = page.locator('.citation-chip').first();
  await expect(firstCitation).toBeVisible({ timeout: 30_000 });

  await firstCitation.click();
  await expect(page.getByTestId('evidence-modal')).toBeVisible();
  await page.getByRole('button', { name: 'Close evidence modal' }).click();

  await page.getByRole('button', { name: 'Timeline' }).click();
  await expect(page.getByTestId('trace-details')).toBeVisible();

  await page.getByTestId('center-pane').getByRole('button', { name: 'Export', exact: true }).click();
  await expect(page.getByText(/Exported to:/)).toBeVisible({ timeout: 15_000 });
});
