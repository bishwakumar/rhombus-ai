# UI tests (Playwright)

Automates the customer journey in the Rhombus web app: source connection, AI-built pipeline, GCS destination and schedule.

- **Runnable from the command line:** `npm test`
- **No fixed sleeps:** every wait is for a real outcome (an element, a log line, or a new file in GCS, polled)
- **Assertions on real outcomes:** the run test checks that a new cleaned file actually lands in the GCS bucket with the right columns

## Setup (once)

Needs Node.js 18+ and the `gcloud` CLI logged in to the project.

```bash
cd ui-tests
npm install
npx playwright install chromium
cp .env.example .env          # then fill in RHOMBUS_PROJECT_URL
npm run auth                  # a browser opens: log in by hand; the session is saved to .auth/
```

The login is done by hand on purpose (it may involve Google sign-in or 2FA). The saved session in `.auth/` is git-ignored. Rerun `npm run auth` when it expires.

**If the login is blocked** (Google: "This browser or app may not be secure"), copy the session from a normal Chrome window instead:

```bash
# Quit Chrome completely first (Cmd+Q), then:
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --remote-debugging-port=9222 --user-data-dir=/tmp/rhombus-chrome
# In that Chrome window, log in to Rhombus and open your project. Then, in another terminal:
npm run auth:chrome
```

## Run

```bash
npm test                      # the journey
npm run report                # HTML report: a video and screenshot of every test
```

The terminal shows one line per test, grouped in journey order, with an `ℹ` line saying what each test found:

```
Rhombus AI: UI journey tests (8 tests)

1 · Source connection
  ✔ GCS source bucket is connected (9.5s)
    ℹ rhombus-source: Connected

2 · AI-built pipeline
  ✔ canvas has Data Input → Custom (AI cleaning step) → Data Output (4.0s)
  – AI Builder adds a cleaning step from a plain-language prompt (skipped: opt-in …)
  ✔ manual run succeeds and writes a new cleaned file to GCS (2.2m)
    ℹ "completed successfully" logged after 2.9 s
    ℹ new file RhombusAI_output_….csv in rhombus-target after 1.9 min
    ℹ header matches the 8 cleaned columns
…
6 passed, 0 failed, 2 skipped (opt-in)
```

Two tests are opt-in, because they change the pipeline or take several minutes:

```bash
RUN_AI_BUILD=1 npm test       # also asks the AI Builder to add a cleaning step (uses AI credits)
RUN_SCHEDULER_WAIT=1 npm test # also watches a */5 schedule for 7 minutes
npm run test:all              # both
```

## Tests

| Group | Test | Checks |
|---|---|---|
| 1 · Source connection | GCS source bucket is connected | The source panel shows `rhombus-source` as Connected |
| 2 · AI-built pipeline | Canvas has Data Input → Custom → Data Output | The AI-built pipeline is in place |
| | AI Builder adds a cleaning step *(opt-in)* | A plain-language prompt produces a pipeline change |
| | Manual run writes a new cleaned file to GCS | Success in the Rhombus log, **a new file in `rhombus-target`**, and the cleaned 8-column header |
| 3 · GCS destination | Data Output exports to the GCS bucket | The output node is configured for `rhombus-target` |
| 4 · Schedule | Hourly schedule shows Active with a next run time | Creating a schedule works and shows a real next-run time |
| 5 · Known issues | **F8:** S3 connection still rejected with the generated policy | Fills in the S3 form and confirms Rhombus still answers "AWS denied Rhombus AI access" |
| | **F4:** an Active */5 schedule still produces no run *(opt-in)* | Creates the schedule and confirms no new file appears in GCS within 7 minutes (polled, not slept) |

### Known issues are confirmed, not skipped

The tests in group 5 check that each problem is **still present**, so they pass while the bug exists and show a normal ✔. If Rhombus fixes one, the test fails with a message such as *"F8 appears FIXED: the S3 source connected. Update findings-log.md and this test"*: the signal to update the finding.

## Fixing a locator

All locators live in [`helpers/selectors.ts`](helpers/selectors.ts); shared navigation is in [`helpers/navigation.ts`](helpers/navigation.ts). The terminal output comes from [`reporter.ts`](reporter.ts), written from the labels visible in the app. If one doesn't match (for example the ▶ Run button, which has no text):

```bash
npm run record                # opens the app with your saved session and Playwright's recorder
```

Click the element; the recorder shows the locator to use. Paste it into `selectors.ts`.

## Videos and popups

- **Every test is recorded on video**, passed or failed, with a screenshot at the end. Open them in the HTML report (`npm run report`, then click a test), or find them in `test-results/<test name>/video.webm`. Each run replaces the previous run's videos; copy any you want to keep.
- **The "Ad blocker detected" popup** is dismissed automatically ("Continue anyway") whenever it appears, by a handler in [`helpers/fixtures.ts`](helpers/fixtures.ts) that every test uses.

## Side effects

- The schedule tests create schedules. Delete them in the Schedule tab afterwards.
- The manual-run test writes one output to `rhombus-target`.
- The opt-in AI Builder test changes the pipeline's cleaning step.
