# UI tests (Playwright)

| | |
|---|---|
| **Code** | [`ui-tests/`](../ui-tests/) |
| **Date** | 5 Oct 2026, AEDT |
| **Result** | 5 of 8 pass; 1 expected failure not yet confirmed; 2 opt-in tests not run |

## What I tested

The customer journey in the Rhombus web app, automated with Playwright: source connection, AI-built pipeline, GCS destination, and schedule. No fixed sleeps; every wait is for a real outcome.

## What I expected

Every step a customer relies on works, apart from the two problems already found by hand: the S3 connection (F8) and the scheduler (F4). Those two are written as tests of what a customer needs, and marked as expected failures.

## What happened

| Test | Result | Notes |
|---|---|---|
| GCS source bucket is connected | ✅ Pass | |
| Canvas has Data Input → Custom → Data Output | ✅ Pass | The AI-built pipeline is in place |
| **Manual run writes a new cleaned file to GCS** | ✅ Pass | Click ▶ → "completed successfully" after 2.9 s → **a new file in `rhombus-target` after 1.9 min** → header is the 8 cleaned columns |
| Data Output exports to the GCS bucket | ✅ Pass | |
| Hourly schedule shows Active with a next run time | ✅ Pass | |
| S3 connects with the generated policy *(expected failure, F8)* | ⚠️ Not confirmed | Last run still used an older test file and stopped on a locator, so it didn't reach the S3 error |
| AI Builder adds a cleaning step *(opt-in)* | Not run | Changes the pipeline and uses AI credits |
| */5 schedule triggers a run *(opt-in, expected failure, F4)* | Not run | Waits up to 7 minutes |

**Observation from the manual-run test:** Rhombus logs "completed successfully" almost **two minutes before** the output file appears in the bucket. Anything that relies on the log message as a signal that data is ready would act too early.

## Problems met while writing the tests

- **Login can't be automated.** Google blocks sign-in from automated browsers ("This browser or app may not be secure"). The session is captured once from a normal Chrome window (`npm run auth:chrome`) and reused.
- **The Run button has no text or accessible name**; it's located by its icon (`svg.lucide-play`). Poor accessibility labelling makes the app harder to test and to use with assistive technology.

## Evidence

- [Manual-run test report](evidence/ui-tests/manual-run-report.png)
- [S3 test report](evidence/ui-tests/s3-test-report.png)
- [Run summary](evidence/ui-tests/run-summary.txt)

## Reproduce

```bash
cd ui-tests && npm install && npx playwright install chromium
npm run auth:chrome      # or: npm run auth
npm test
```
