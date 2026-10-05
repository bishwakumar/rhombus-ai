# 04 – Schema drift: add a column

| | |
|---|---|
| **Input** | [`datasets/04-schema-add-column.csv`](../datasets/04-schema-add-column.csv): 500 rows, 9 columns |
| **Date** | 5 Oct 2026, AEDT |
| **Did Rhombus pass it?** | ✅ Yes |
| **Should it have?** | ⚠️ Passing is acceptable, but it should warn that a column was dropped |
| **Pipeline stopped?** | No |
| **Chatbot fix worked?** | Not tested |
| **Severity** | Medium |

## What I changed

Added `discount_code` at the end (`SPRING10`, `WELCOME5`, `VIP20`, `FREESHIP` or blank).

## What I expected

The code keeps only the 8 expected columns, so the run should **succeed** and `discount_code` should be **dropped silently**.

## What happened

- The input preview showed **9 columns**, including `discount_code` (checked by hand).
- The run **completed** with the original **8 columns**; `discount_code` was dropped with no warning.
- All other values are correct, and the output is **byte-identical to the baseline output**, the correct result for this case.
- One dataset selection produced **four outputs in 18 seconds** (12:01:25–12:01:43) with no extra clicks: [gcs-target-listing-2026-10-05.txt](evidence/platform/gcs-target-listing-2026-10-05.txt).

Run 1 was a setup attempt and isn't used.

## What the logs said

The run completed with no error or warning. *(The log entry wasn't saved.)*

Because the output equals the baseline output, **nothing in Rhombus's own records shows which input this run used**; only the manual preview check confirms it.

## What the chatbot said

Not tested.

## Did the fix work?

Not tested.

## Reproduce

```bash
python3 runner/run_cases.py --cases 04-schema-add-column
# Press Enter, then select _04_schema_add_column (preview shows 9 columns).
python3 data-validation/validate.py 04-schema-add-column
```

## Validator

| Run | Verdict | Why |
|---|---|---|
| 2 | ✔ PASS (with warnings) | Values correct. Warnings: `discount_code` silently dropped; identical to baseline (expected); formatting |

## Not captured

Input preview screenshot; Rhombus log entry.
