import { test, expect } from '../helpers/fixtures';
import { ui } from '../helpers/selectors';
import { listCsv, newSince, header } from '../helpers/gcs';
import { note } from '../helpers/note';

const OUTPUT = process.env.GCS_OUTPUT_BUCKET ?? 'rhombus-target';
const EXPECTED_COLUMNS = ['order_id', 'customer_name', 'email', 'order_date',
                          'amount_usd', 'quantity', 'country', 'status'];

test.describe('2 · AI-built pipeline', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(process.env.RHOMBUS_PROJECT_URL!);
    await expect(ui(page).canvasTab).toBeVisible();
  });

  test('canvas has Data Input → Custom (AI cleaning step) → Data Output', async ({ page }) => {
    const u = ui(page);
    await expect(u.node('Data Input')).toBeVisible();
    await expect(u.node('Custom')).toBeVisible();
    await expect(u.node('Data Output')).toBeVisible();
    note('Data Input → Custom → Data Output');
  });

  test('AI Builder adds a cleaning step from a plain-language prompt', async ({ page }) => {
    test.skip(!process.env.RUN_AI_BUILD, 'opt-in, set RUN_AI_BUILD=1 (changes the pipeline, uses AI credits)');
    test.setTimeout(8 * 60_000);
    const u = ui(page);
    await u.aiBuilderTab.click();
    await u.chatInput.fill('Add a cleaning step that trims spaces and title-cases customer_name.');
    await u.chatInput.press('Enter');
    await expect(page.getByText(/Modified pipeline|Pipeline changes compiled/i).first())
      .toBeVisible({ timeout: 7 * 60_000 });
    await expect(u.node('Custom')).toBeVisible();
    note('AI Builder reported a pipeline change; cleaning step present');
  });

  test('manual run succeeds and writes a new cleaned file to GCS', async ({ page }) => {
    test.setTimeout(5 * 60_000);
    const u = ui(page);
    const before = listCsv(OUTPUT);
    const t0 = Date.now();

    await u.runButton.click();

    // Real outcome 1: Rhombus logs a successful run
    await u.logsTab.click();
    await expect(u.logEntry(/Pipeline (execution )?completed successfully/)).toBeVisible({ timeout: 3 * 60_000 });
    const logged = (Date.now() - t0) / 1000;

    // Real outcome 2: a new output file exists in the destination bucket (polled, no sleeps)
    await expect.poll(() => newSince(OUTPUT, before).length, {
      timeout: 3 * 60_000, intervals: [3_000, 5_000, 10_000],
    }).toBeGreaterThan(0);
    const landed = (Date.now() - t0) / 1000;

    // Real outcome 3: the file has the cleaned schema
    const [newest] = newSince(OUTPUT, before);
    expect(header(newest)).toEqual(EXPECTED_COLUMNS);

    note(`"completed successfully" logged after ${logged.toFixed(1)} s`);
    note(`new file ${newest.split('/').pop()} in ${OUTPUT} after ${(landed / 60).toFixed(1)} min`);
    note('header matches the 8 cleaned columns');
  });
});
