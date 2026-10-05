# Findings log

Running record of everything observed while testing Rhombus AI. Times are AEDT (UTC+11) on 4 Oct 2026 unless marked otherwise; earlier times on 3 Oct are AEST (UTC+10). Daylight saving started in Sydney early on 4 Oct.

## Environment

| Item | Value |
|---|---|
| GCP project | `ambient-climate-420216` |
| Source | `gs://rhombus-source/input/orders.csv` (versioning on) |
| Destination | `gs://rhombus-target/` (Rhombus names outputs `RhombusAI_output_<epoch ms>.csv`) |
| Run log backup | `gs://rhombus-runs/runs.csv` (versioning on) |
| Pipeline | Data Input → Custom (`clean_orders`, `llm_node_1`) → Data Output |
| Pipeline code | `code_sha=3ca80b148200` (original, AI-generated) |
| Baseline output MD5 | `f1a7904a06a099d9097bc420e51a5ca9` |

## Case status

| Case | Run | Validated | Chatbot | Observation |
|---|---|---|---|---|
| 00-baseline | ✅ 3 runs, byte-identical | ✅ WARN (formatting only) | n/a | README |
| 01-schema-drop-column | ✅ | ✅ | ✅ | ✅ written |
| 02-schema-rename-column | ✅ failed on `'amount_usd'` (17:06:23) | ✅ no output | ⬜ pending | 🟡 TODOs |
| 03-schema-type-change | ✅ ran "successfully" (output 11:49:06, 33.4 KB) | ✅ FAIL: `order_date` 100% blank (baseline 8.7%) | ⬜ optional (no error to give) | ⬜ |
| 04-schema-add-column | ✅ ran "successfully"; preview confirmed 9 columns | ✅ WARN: `discount_code` silently dropped | n/a (no error) | ⬜ |
| 05-schema-combined | ✅ stopped on `'email'` (12:08, run 1) | ⏹ STOPPED (3 attempts) | ✅ diagnosis incomplete; fix claimed, not applied (run 3, 13:04, same code_sha) | ⬜ |
| 06-semantic-cents | ✅ ran (Rhombus result: _TODO confirm success/no warning_) | ✅ FAIL: semantics, 423/425 amounts > $2,500 (max 199,849.00) | n/a (no error) | ⬜ |
| 07-semantic-date-swap | ✅ ran successfully, no warning (output 1791167932998) | ✅ FAIL: semantics, 208 of 429 dates outside Jan–Mar, months 1–12 | n/a (no error) | ⬜ |

## Findings

### Critical

**F1. Rhombus does not re-read the source file on each run.**
Case 01 run 1: drift file uploaded and verified at 14:48:52 (28.2 KB, generation `1791085732256835`). The run completed successfully at 14:49:07, and its output was byte-identical to the baseline output (MD5 `f1a7904a…`), including 383 email values that don't exist in the new input. The Data Input preview still showed the old file. No error, warning or log entry.

**F2. Refreshing source data is limited and unreliable.**
Manual sync is available only every 30 minutes and did not reliably update the data. Reconnecting the data source was the only dependable method, and it must be done manually before every run. A scheduled pipeline therefore can't pick up a changed source.

**F3. Reconnecting the source triggers unrequested pipeline runs (reproduced 3 times).**
2 runs at 14:24:02–04, 3 runs at 16:04:43–50, and 3 runs at 16:21:53–56 (deliberate test, no run pressed). Each wrote an output to GCS. No runs occurred between reconnections. Most likely cause: selecting a dataset starts a run by itself (F16), and reconnecting selects datasets. Earlier hypothesis: three deleted schedules still active in the background; not confirmed from logs.

### High

**F4. Scheduler never runs.**
3 Oct: schedules `*/2`, `*/5` and hourly at minute 01, all Active. No runs between 15:19:54 and 17:02:02 AEST (74 expected: 51 + 21 + 2). "Next run" went blank after each due time. No failure notification, even with notifications on. Manual run at 17:02 succeeded. Followed the documented setup and troubleshooting steps.

**F5. Chatbot claims fixes that are not applied.**
3 Oct: replied "All rules are applied correctly" while the canvas had no cleaning node (Data Input → Data Output only). 4 Oct, case 01: reported "The clean_orders node has been fixed on the canvas"; the node's code afterwards was unchanged, and case 02 at 17:06:23 still ran `code_sha=3ca80b148200`.

Reproduced in case 05: the chatbot said it relabelled the prompt "v2" to "force the pipeline to regenerate fresh code" and explained the pipeline "was executing old cached code from before the missing-column fix was added" (confirming the prompt/code desync). Run 3 at 13:04 still failed on `'email'` with the same `code_sha=3ca80b148200`, so no regeneration happened.

**F6. Chatbot fixes are applied without confirmation and cannot be undone.**
No version history or undo for nodes. The only way back is asking the chatbot to revert its own change, which may introduce new errors.

**F7. Chatbot's proposed fix for case 01 would hide drift.**
Injects any missing expected column as blanks, for all columns including `order_id`. That would collapse deduplication to one row if `order_id` were missing, and silently blank every amount on a rename.

**F23. Chatbot diagnoses only the first error in a multi-change drift (case 05).**
Four changes were made (email dropped, amount_usd renamed, order_date to timestamps, discount_code added). The log reports only `'email'`; the chatbot addressed only `'email'`. Its blank-column fix, had it run, would have blanked every amount (rename ignored) and every date (timestamps unparsed), and dropped discount_code, all silently.

**F8. S3 connection fails with a correct, generated policy.**
3 Oct: error "AWS denied Rhombus AI access to the whole bucket… policy is missing or does not match". The bucket policy contained the exact generated statements (pasted and via CloudFormation), both Rhombus principals, SSE-S3 encryption, correct region and bucket name. Switched to a GCS source. Support request drafted.

### Medium

**F9. The platform changes data before any transformation.**
A plain Data Input → Data Output pipeline converted dates to YYYY-MM-DD and turned `n/a` / `N/A` into blanks. The Data Input preview labels `order_date` as DateTime (`2026-03-09T00:00:00`). The generated code expects pre-parsed Timestamps.

**F10. Output formatting rules not honoured (reproduced on two datasets).**
The cleaning code returns `"5"` and `"642.90"`, but the delivered files contain `5.0` and `642.9`. On v2 data: 405 quantities and 45 amounts. Two fix prompts were acknowledged; outputs stayed byte-identical. The export step re-types values.

**F11. Error logs are hard to act on.**
They name the step and column (`'email'`, `'amount_usd'`) and are structured JSON, but give no error type, say "LLM execution failed" for ordinary code errors, truncate the code inside a platform helper (`_safe_to_timedelta_wrapper`) before the failing line, and give no line number. The node is called "Custom" on the canvas but `clean_orders` / `llm_node_1` in logs. A rename isn't recognised as a rename.

**F12. Logs omit key facts.**
"242 row(s) affected, 406 cell(s) modified" doesn't mention deleted duplicate rows. No trigger source (manual or scheduled). Nothing logged for missed schedules or stale-data runs. A run at 15:19:54 (3 Oct) finished in the same second with no transformation line and wrote no output, yet reported success.

**F15. Datasets in the Data Input picker are all named `placeholder_file`.**
5 Oct, 10:53: ten datasets listed, every one named `placeholder_file`; the Data Input node shows `incremental_mar`, which matches nothing created. The only way to tell datasets apart is the preview (eye icon). Risk: running the pipeline on the wrong data without noticing. Evidence: `evidence/dataset-picker-placeholder-names.png`.

**F16. Selecting a dataset starts a pipeline run without Apply or Run.**
5 Oct, 10:53: clicking a dataset in the picker started the pipeline immediately; it failed at `clean_orders` (`code_sha=3ca80b14820…`). Likely root cause of F3: every connection, refresh or reselection selects a dataset, which triggers a run. _To confirm: select a dataset, note the time, check Logs and `rhombus-target`._

**F17. Deleting a dataset from the picker is unreliable.**
5 Oct: _TODO: what happens exactly (nothing / reappears / error), and after how many attempts._

**F18. Only one GCS bucket can be connected at a time.**
5 Oct: the Third Party Data panel allows a single GCS connection (`rhombus-source`); a second bucket can't be added. Per-bucket sources per case were abandoned for one file per case in `input/`.

**F19. Silent data loss when a column's type changes (case 03).**
`order_date` changed to Unix timestamps. The run completed with no error or warning; every `order_date` in the output is blank (100% vs 8.7% baseline). Only the independent validator's blank-rate check caught it.

**F20. New columns are silently dropped (case 04).**
`discount_code` added to the input (9 columns, confirmed in the input preview). The run completed; the output has the original 8 columns, with no warning that data was discarded.

**F21. No data lineage in outputs or logs.**
Nothing in the output file or the run log records which input dataset produced it. In case 04 the correct output is identical to the baseline output, so Rhombus's own records cannot show which data the run processed; only the input preview, observed manually, could confirm it.

**F24. Dollars-to-cents drift passes through undetected (case 06).**
Amounts written in cents under the same `amount_usd` column. The pipeline cleaned them exactly per the rules and delivered values 100× too high (max 199,849.00 vs 1,998.49), with no warning. Schema, row counts, blank rates and rule checks all passed; only the validator's range check (423 of 425 amounts above $2,500) caught it. The 2 unflagged amounts are orders under $25.

**F25. Day/month swap passes through undetected, and part of it is undetectable by range checks (case 07).**
Slash/dash dates written day-first. The run completed with no warning; dates were read month-first. 252 of 470 order dates changed meaning: 208 fall outside the true January–March window (all 12 months appear; 42 are in the future, after 5 Oct 2026) and were caught by the validator's range check. The other 44 swap into another valid January–March date (e.g. 3 Jan becomes 1 Mar) and **cannot be detected from the output at all**. Only the source system's format contract could prevent them.

### Low

**F22. Rhombus renames source files.** `03-schema-type-change.csv` appears as `_03_schema_type_change` (hyphens to underscores, extension dropped, leading underscore added), so names in Rhombus don't match the bucket.

**F13.** One click produced two outputs 18 seconds apart (2:54:39 and 2:54:57 PM, 3 Oct); unconfirmed whether it was a double click.

**F14.** Chatbot summary inaccuracies: called originally missing countries "unmapped"; wrote `None` for the source value `none`.

### Positive

**P1.** Once the cleaning step was on the canvas, every value was correct: 470/470 rows on name, email, date, country and status; amount and quantity correct apart from formatting.
**P2.** Deterministic: 3 baseline runs from 3 separate uploads were byte-identical.
**P3.** Schema drift that removes or renames a column stops the pipeline (cases 01, 02) rather than writing bad data.
**P4.** The chatbot diagnosed case 01 correctly and named the `KeyError`, more clearly than the log.
**P5.** The S3 error message was well written (specific cause and two fixes), even though the cause was wrong.

## Method notes

- Each case is loaded by `runner/run_cases.py`, which verifies the upload and records MD5 and GCS generation in `results/runs.csv`.
- The source must be reconnected in Rhombus before each run; the runner lists the expected columns to check against the input preview.
- The runner only captures outputs created after Enter is pressed, and logs others as ignored.
- Every output is validated by `data-validation/validate.py`, which is independent of Rhombus.
- Before each case, the pipeline state is confirmed by running the baseline and matching MD5 `f1a7904a…`.

## Open items

- Case 02: chatbot step.
- Cases 03–07: run, validate, chatbot.
- Confirm from Rhombus logs whether the reconnection runs mention schedules (F3).
- Confirm `runs.csv` rows for case 01 run 2 and case 02 run 1 (`no_output` / missing).




/////////////

Case	Rhombus	Validator
00 baseline	✅ Success	✔ PASS (with warnings)
01 drop column	⏹ Stopped ('email'); first run used stale data	✘ FAIL (stale run)
02 rename column	⏹ Stopped ('amount_usd')	⏹ STOPPED
03 type change	✅ "Success"	✘ FAIL: dates 100% blank
04 add column	✅ "Success"	✔ PASS (with warnings): column silently dropped
05 combined	⏹ Stopped ('email'), chatbot fix ineffective	⏹ STOPPED
06 cents	✅ "Success"	✘ FAIL: amounts 100× too high
07 date swap	✅ "Success"	✘ FAIL: 208 dates out of range; 44 undetectable