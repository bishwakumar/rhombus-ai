# 00 – Baseline

| | |
|---|---|
| **Input** | [`datasets/00-baseline.csv`](../datasets/00-baseline.csv): 500 rows, 8 columns |
| **Correct answer** | [`datasets/00-baseline.expected.csv`](../datasets/00-baseline.expected.csv): 470 rows |
| **Did Rhombus pass it?** | ✅ Yes |
| **Should it have?** | ✅ Yes |
| **Validator** | ✔ PASS (with warnings): every value correct, number formatting off |
| **Severity** | Low |

## What it is

An orders file with planted problems: 20 exact duplicate rows, 10 repeated order IDs with different data, missing values, mixed date formats, `$` and `USD` in amounts, number words in quantities, country abbreviations and mixed-case statuses. Every problem is counted in [`datasets/answer_key.md`](../datasets/answer_key.md).

The pipeline was built with the AI Builder only: **Data Input → Custom (`clean_orders`) → Data Output (GCS)**.

## What I expected

All 8 cleaning rules applied: 470 rows out, matching `00-baseline.expected.csv`.

## What happened

### Building the pipeline (3 Oct, first dataset)

1. **The chatbot said the work was done when the pipeline had no cleaning step.** It replied *"All rules are applied correctly"* with a correct-looking summary, but the canvas showed only Data Input → Data Output. The cleaning had been done once inside the chat. The pipeline output still had all 283 rows uncleaned.
   Evidence: [canvas](evidence/00-baseline/canvas-no-cleaning-step.png), [chatbot reply](evidence/00-baseline/chatbot-claim-all-rules-applied.md), [output](evidence/00-baseline/first-dataset/output_1_no_cleaning_step.csv).
2. **The platform changed data with no cleaning step present.** That pass-through output had every date converted to `YYYY-MM-DD` and `n/a`/`N/A` turned into blanks.
3. **After a cleaning node was added, the values were correct**, but quantities came out as `5.0` and amounts lost trailing zeros (`642.9`). Two requests to the chatbot to fix this were acknowledged; the next two outputs were **byte-identical** to the one before (MD5 `0bdaf6b7…` three times). Evidence: [md5.txt](evidence/00-baseline/first-dataset/md5.txt), [scorecard](evidence/00-baseline/first-dataset/rhombus_cleaning_scorecard.xlsx).

### Baseline runs (4 Oct, final dataset)

| Check | Result |
|---|---|
| Rows | 500 in, 470 out, every order once |
| Names, emails, dates, countries, statuses | All 470 correct |
| Amounts, quantities | Values correct; 45 amounts lose a trailing zero, all 405 quantities written as `5.0` |
| Repeatability | 4 runs from 4 separate uploads, all **byte-identical** (MD5 `f1a7904a06a099d9097bc420e51a5ca9`) |

The generated code returns `"642.90"` and `"5"` as text; the values are turned back into numbers when the file is written, so the formatting issue sits in the export step, outside the code the chatbot can change.

## Not as the brief intended

- **GCS source instead of S3.** The S3 connection failed every time with *"AWS denied Rhombus AI access to the whole bucket…"*, even with the exact generated bucket policy applied. Evidence: [s3-error-and-checks.md](evidence/s3-connection/s3-error-and-checks.md).
- **Manual runs instead of a scheduled run.** Three schedules showed **Active** but never ran: 74 runs expected between 3:20 and 5:02 PM, 0 actual, no alert. Evidence: [execution log](evidence/scheduler/execution-log-2026-10-03.txt), [schedule list](evidence/scheduler/schedule-list-2026-10-03.txt), [screenshots](evidence/scheduler/), [spreadsheet](evidence/scheduler/rhombus_scheduler_evidence.xlsx).

## Reproduce

```bash
python3 runner/run_cases.py --cases 00-baseline --runs 3
python3 data-validation/validate.py 00-baseline
```

## Evidence

- Outputs: `outputs/00-baseline__run1.csv` … `__run4.csv`
- Validator: `results/validation/00-baseline__run1.json` …
- Run records: `results/runs.csv`
