import { test, expect } from '../helpers/fixtures';
import { ui } from '../helpers/selectors';
import { listCsv, newSince } from '../helpers/gcs';
import { note } from '../helpers/note';
import { openSources } from '../helpers/navigation';

const OUTPUT = process.env.GCS_OUTPUT_BUCKET ?? 'rhombus-target';

/**
 * Known issues found during testing. Each test confirms the problem is STILL PRESENT, so it
 * passes while the bug exists. If Rhombus fixes it, the test fails with a message saying so:
 * update observations/findings-log.md and the test.
 */
test.describe('5 · Known issues (confirmed still present)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(process.env.RHOMBUS_PROJECT_URL!);
    await expect(ui(page).canvasTab).toBeVisible();
  });

  test('F8: S3 connection is still rejected with the generated bucket policy', async ({ page }) => {
    test.setTimeout(60_000);            // the whole test, page load included, gets at most 1 minute
    const u = ui(page);
    await openSources(page);
    await u.addDataSourcesButton.click();
    await u.amazonS3Option.click();
    await u.bucketField.fill(process.env.S3_BUCKET ?? 'rhombus-ai');
    await u.connectS3Button.click();

    // Real outcome: Rhombus answers with either a connected source or the denial message
    const denied = page.getByText(/AWS denied Rhombus AI access/i).first();
    await expect(denied.or(u.connectedBadge)).toBeVisible({ timeout: 30_000 });
    if (await u.connectedBadge.isVisible()) {
      throw new Error('F8 appears FIXED: the S3 source connected. Update findings-log.md and this test');
    }
    note(`Rhombus: "${(await denied.innerText()).trim().slice(0, 90)}…"`);
  });

  test('F4: an Active */5 schedule still produces no run within 7 minutes', async ({ page }) => {
    test.skip(!process.env.RUN_SCHEDULER_WAIT, 'opt-in, set RUN_SCHEDULER_WAIT=1 (watches the bucket for 7 minutes)');
    test.setTimeout(9 * 60_000);
    const u = ui(page);
    const before = listCsv(OUTPUT);

    await u.scheduleTab.click();
    await u.addScheduleButton.click();
    await u.frequencySelect.click();
    await u.frequencyOption('Custom').click();
    await page.getByRole('textbox').last().fill('*/5 * * * *');
    await u.createButton.click();
    await expect(u.activeBadge.last()).toBeVisible();

    // Watch the bucket for 7 minutes (polled). A new file would mean the schedule ran.
    let ran = false;
    try {
      await expect.poll(() => newSince(OUTPUT, before).length, { timeout: 7 * 60_000, intervals: [15_000] })
        .toBeGreaterThan(0);
      ran = true;
    } catch { /* no run within the window: the issue is still present */ }
    expect(ran, 'F4 appears FIXED: the schedule produced a run. Update findings-log.md and this test').toBe(false);

    note('schedule shows Active; no output in 7 minutes (two */5 slots missed)');
    note(`schedule card now shows "${(await u.nextRun.last().innerText()).trim()}"`);
    note('delete the schedule afterwards in the Schedule tab');
  });
});