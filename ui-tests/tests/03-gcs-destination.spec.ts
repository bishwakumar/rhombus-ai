import { test, expect } from '../helpers/fixtures';
import { ui } from '../helpers/selectors';
import { note } from '../helpers/note';

test.describe('3 · GCS destination', () => {
  test('Data Output node exports to the GCS destination bucket', async ({ page }) => {
    await page.goto(process.env.RHOMBUS_PROJECT_URL!);
    const u = ui(page);
    await expect(u.canvasTab).toBeVisible();
    await u.node('Data Output').click();
    const bucket = process.env.GCS_OUTPUT_BUCKET ?? 'rhombus-target';
    await expect(page.getByText(bucket).first()).toBeVisible();
    note(`destination: ${bucket}`);
  });
});
