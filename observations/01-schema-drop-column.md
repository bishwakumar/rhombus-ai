# 01 – Schema drift: drop a column

| | |
|---|---|
| **Input** | [`datasets/01-schema-drop-column.csv`](../datasets/01-schema-drop-column.csv): 500 rows, 7 columns |
| **Date** | 4 Oct 2026, AEDT |
| **Did Rhombus pass it?** | First run: **yes, on stale data**. After a refresh: **stopped** |
| **Should it have?** | No. Stopping is right |
| **Pipeline stopped?** | ✅ Yes, once it read the new file |
| **Chatbot fix worked?** | ❌ No. Reported as applied; the running code never changed |
| **Severity** | **High** |

## What I changed

Removed the `email` column. Everything else identical to the baseline.

## What I expected

The cleaning code reads `email` directly, so the pipeline should **stop** with a missing-column error and write nothing.

## What happened

### Run 1: Rhombus ignored the new file

| Step | Time | Evidence |
|---|---|---|
| New file uploaded over `input/orders.csv` (28.2 KB, generation `1791085732256835`) | 14:48:52 | [gcs-source-listing.txt](evidence/01-schema-drop-column/gcs-source-listing.txt) |
| Run triggered, without refreshing the source | 14:49 | |
| **Completed successfully**; output `RhombusAI_output_1791085746529.csv` | 14:49:07 | [gcs-target-listing-2026-10-04.txt](evidence/platform/gcs-target-listing-2026-10-04.txt) |
| Output **byte-identical to the baseline** (MD5 `f1a7904a…`), with 383 email addresses the input doesn't have | | [stale-output-md5.txt](evidence/01-schema-drop-column/stale-output-md5.txt) |
| Input preview still showed the old file, with `email` | 14:55 | [input-preview-stale.png](evidence/01-schema-drop-column/input-preview-stale.png) |

Rhombus processed its earlier copy of the source and reported success. Nothing indicated stale data.

To make Rhombus read the new file: the manual sync is available only every 30 minutes and did not reliably update the data; **reconnecting the source** was the only method that worked every time.

### Run 2: the real result

After reconnecting (preview: 7 columns), the run **stopped** at 15:09:00. Nothing was written to GCS.

## What the logs said

From [failure-log.json](evidence/01-schema-drop-column/failure-log.json) ([screenshot](evidence/01-schema-drop-column/failure-notification.png)):

```
"status": "error",
"message": "Pipeline failed at clean_orders: LLM execution failed (code_sha=3ca80b148200): 'email'
            --- Generated code --- import pandas as pd import numpy as np
            def _safe_to_timedelta_wrapper(arg, *args, **kwargs): try: arg_series = pd.Series(arg)
            except Exception: arg_series = a…",
"nodeLabel": "clean_orders"
```

**Partly clear.**
- ✅ Names the step (`clean_orders`) and the column (`'email'`), and gives a code version (`code_sha`).
- ❌ No plain explanation: `'email'` alone is a raw Python KeyError. "Column 'email' not found in input" would be clear.
- ❌ Says "**LLM** execution failed", though it was the generated code that failed, not the AI model.
- ❌ The attached code is cut off inside a platform helper (`_safe_to_timedelta_wrapper`), before the line that failed; no line number.
- ❌ The canvas calls the node "Custom"; the log calls it `clean_orders` / `llm_node_1`.
- ❌ Run 1 (stale data) produced no warning at all.

## What the chatbot said

"Ask Chatbot" on the error, nothing added. Full reply: [chatbot-reply.md](evidence/01-schema-drop-column/chatbot-reply.md).

> The `clean_orders` node has been fixed on the canvas. **Root cause:** The new `orders` source … has 7 columns — no `email` column … caused the `KeyError: 'email'` crash. **Fix applied:** The node now begins by checking for and injecting any missing expected columns as blank strings…

- **Diagnosis: correct**, and clearer than the log.
- **Changed the pipeline without asking.**
- **The fix would hide problems:** every missing column becomes blank with no warning, including `order_id` (which would collapse the deduplication to a single row).

## Did the fix work?

**No.**
- The node's code was unchanged afterwards.
- Every later failure still shows `code_sha=3ca80b148200` (case 02 at 17:06:23; case 05 at 12:08 and 13:04).
- The saved success logs show the instruction only in the node's **prompt**, while the **code** is character-for-character the original: [prompt-vs-code.md](evidence/03-schema-type-change/prompt-vs-code.md).

## Reproduce

```bash
python3 runner/run_cases.py --source-mode fixed --cases 01-schema-drop-column
# Reconnect the source in Rhombus, check the preview shows 7 columns, press Enter, then run.
# Skip the reconnect to reproduce run 1 (stale data).
python3 data-validation/validate.py 01-schema-drop-column
```

## Validator

| Run | Verdict | Why |
|---|---|---|
| 1 | ✘ FAIL | 383 emails that aren't in the input; byte-identical to the baseline output |
| 2 | ⏹ STOPPED | Pipeline stopped on `'email'` |
