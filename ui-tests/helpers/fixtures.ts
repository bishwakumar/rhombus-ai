import { test as base, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

const VIDEO_DIR = path.join(__dirname, '..', 'videos');

/** File-safe name for a test, e.g. "2 · AI-built pipeline › manual run…" → "2-ai-built-pipeline--manual-run…". */
function slug(parts: string[]): string {
  return parts.join(' -- ').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 120);
}

/**
 * Shared test setup. Every test gets a page that:
 *  - dismisses the "Ad blocker detected" popup automatically ("Continue anyway"), and
 *  - keeps one video per test in videos/. An existing video is not replaced,
 *    unless RERECORD=1 is set.
 */
export const test = base.extend({
  page: async ({ page }, use, testInfo) => {
    await page.addLocatorHandler(
      page.getByText(/ad ?blocker detected/i).first(),
      async () => {
        await page.getByRole('button', { name: /continue anyway/i })
          .or(page.getByText(/continue anyway/i))
          .first()
          .click();
      },
    );

    await use(page);

    const video = page.video();
    if (!video || testInfo.status === 'skipped') return;
    const dest = path.join(VIDEO_DIR, `${slug(testInfo.titlePath.slice(1))}.webm`);
    if (fs.existsSync(dest) && !process.env.RERECORD) {
      testInfo.annotations.push({ type: 'info', description: `video kept: videos/${path.basename(dest)}` });
      return;
    }
    fs.mkdirSync(VIDEO_DIR, { recursive: true });
    await page.close();                 // the video file is complete once the page closes
    await video.saveAs(dest);
    // testInfo.annotations.push({ type: 'info', description: `video saved: videos/${path.basename(dest)}` });
  },
});

export { expect };