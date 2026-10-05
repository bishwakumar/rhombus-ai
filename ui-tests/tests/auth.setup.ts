import { test, expect } from '@playwright/test';
import fs from 'node:fs';

/**
 * One-off login. Run with `npm run auth`: a browser opens on your project,
 * you log in by hand, and the session is saved to .auth/state.json (git-ignored).
 * The test waits for the canvas to appear; it doesn't sleep.
 */
test('log in by hand and save the session', async ({ page }) => {
  test.setTimeout(10 * 60_000);
  const url = process.env.RHOMBUS_PROJECT_URL;
  test.skip(!url, 'Set RHOMBUS_PROJECT_URL in .env');

  await page.goto(url!);
  console.log('\nLog in to Rhombus in the browser window. Waiting for the pipeline canvas…\n');
  await expect(page.getByText('Canvas', { exact: true }).first()).toBeVisible({ timeout: 9 * 60_000 });

  fs.mkdirSync('.auth', { recursive: true });
  await page.context().storageState({ path: '.auth/state.json' });
});
