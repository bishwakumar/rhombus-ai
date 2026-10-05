import { test, expect } from '../helpers/fixtures';
import { ui } from '../helpers/selectors';
import { note } from '../helpers/note';

test.describe('4 · Schedule', () => {
  test('an hourly schedule can be created and shows Active with a next run time', async ({ page }) => {
    await page.goto(process.env.RHOMBUS_PROJECT_URL!);
    const u = ui(page);
    await expect(u.canvasTab).toBeVisible();
    await u.scheduleTab.click();
    const before = await u.scheduleCards.count();

    await u.addScheduleButton.click();
    await u.frequencySelect.click();
    await u.frequencyOption('Hourly').click();
    await u.createButton.click();

    await expect(u.scheduleCards).toHaveCount(before + 1);
    await expect(u.activeBadge.last()).toBeVisible();
    // A real next-run time ("Next run: in 59 mins"), not the blank field seen in testing
    await expect(u.nextRun.last()).toHaveText(/Next run:\s*\S+/);
    note(`schedule created: Active, "${(await u.nextRun.last().innerText()).trim()}"`);
    note('delete it afterwards in the Schedule tab');
  });
});
