import { expect, Page } from '@playwright/test';
import { ui } from './selectors';

/** Opens the "Third Party Data" panel the way a user does: via the Data Input node. */
export async function openSources(page: Page) {
  const u = ui(page);
  await u.node('Data Input').click();
  await u.sourcesEntry.click();
  await expect(u.thirdPartyData).toBeVisible();
}
