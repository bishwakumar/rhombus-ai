import { test, expect } from '../helpers/fixtures';
import { ui } from '../helpers/selectors';
import { note } from '../helpers/note';
import { openSources } from '../helpers/navigation';

test.describe('1 · Source connection', () => {
  test('GCS source bucket is connected', async ({ page }) => {
    await page.goto(process.env.RHOMBUS_PROJECT_URL!);
    const u = ui(page);
    await expect(u.canvasTab).toBeVisible();
    await openSources(page);
    const bucket = process.env.GCS_SOURCE_BUCKET ?? 'rhombus-source';
    await expect(u.sourceCard(bucket)).toBeVisible();
    await expect(u.connectedBadge).toBeVisible();
    note(`${bucket}: Connected`);
  });
});
