import { expect, test } from '@playwright/test';

test('missing API key warning is shown', async ({ page }) => {
  await page.goto('/?test_mode=1&static=1&simulate_no_key=1');
  await page.waitForFunction(() => window.__READY === true);
  await expect(page.getByTestId('missing-key-banner')).toBeVisible();
});

test('docker fallback warning is shown', async ({ page }) => {
  await page.goto('/?test_mode=1&static=1&simulate_docker_missing=1');
  await page.waitForFunction(() => window.__READY === true);
  await expect(page.getByTestId('docker-fallback-banner')).toBeVisible();
});

test('disconnect banner supports reconnect', async ({ page }) => {
  await page.goto('/?test_mode=1&static=1&simulate_disconnect=1');
  await page.waitForFunction(() => window.__READY === true);
  await expect(page.getByText(/Event stream disconnected/)).toBeVisible();
  await page.getByRole('button', { name: 'Reconnect' }).click();
  await expect(page.getByText(/Event stream disconnected/)).not.toBeVisible();
});
