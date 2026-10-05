import { defineConfig } from '@playwright/test';
import 'dotenv/config';

export default defineConfig({
  testDir: './tests',
  timeout: 3 * 60_000,            // per test; long waits are on real outcomes, not sleeps
  expect: { timeout: 30_000 },
  fullyParallel: false,
  workers: 1,                     // one pipeline, one browser: tests run in order
  retries: 0,
  reporter: [['./reporter.ts'], ['html', { open: 'never' }]],
  use: {
    actionTimeout: 30_000,        // a missing element fails after 30 s instead of hanging
    navigationTimeout: 60_000,
    baseURL: process.env.RHOMBUS_BASE_URL,
    trace: 'retain-on-failure',
    screenshot: 'on',             // a screenshot at the end of every test
    video: 'on',                  // a video of every test, passed or failed
  },
  projects: [
    // One-off: log in by hand, save the session
    { name: 'auth', testMatch: /auth\.setup\.ts/ },
    // The journey, reusing the saved session
    { name: 'journey', testMatch: /.*\.spec\.ts/, use: { storageState: '.auth/state.json' } },
  ],
});
