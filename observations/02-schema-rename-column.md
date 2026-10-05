# 02 – Schema drift: rename a column

| | |
|---|---|
| **Input** | [`datasets/02-schema-rename-column.csv`](../datasets/02-schema-rename-column.csv): 500 rows, 8 columns |
| **Date** | 4 Oct 2026, AEDT |
| **Did Rhombus pass it?** | ❌ Stopped |
| **Should it have?** | No. Stopping is right; recognising the rename would be better |
| **Pipeline stopped?** | ✅ Yes |
| **Chatbot fix worked?** | Not tested |
| **Severity** | Medium |

## What I changed

Renamed `amount_usd` to `total_amount`. Values and every other column unchanged.

## What I expected

The code reads `amount_usd` directly, so the pipeline should **stop** and write nothing.

## What happened

Before this case, the baseline was rerun and produced the same output as before (MD5 `f1a7904a…`), so the pipeline was unchanged. The source was reconnected and the preview showed `total_amount` in place of `amount_usd`.

The run **stopped** at 17:06:23. Nothing was written to GCS. As predicted.

The `code_sha` is the same as before the case 01 chatbot "fix", which confirms that fix wasn't running.

## What the logs said

From [failure-log.json](evidence/02-schema-rename-column/failure-log.json):

```
"message": "Pipeline failed at clean_orders: LLM execution failed (code_sha=3ca80b148200): 'amount_usd'
            --- Generated code --- … arg_serie…"
```

**Partly clear**: the same strengths and weaknesses as [case 01](01-schema-drop-column.md#what-the-logs-said), plus:
- ❌ **The rename isn't recognised.** `total_amount` is in the input, but the log only says `amount_usd` is missing.

## What the chatbot said

**Not tested.** The fix it gave for case 01 shows the risk: here it would create an empty `amount_usd` and drop `total_amount`, losing every amount without an error. A good fix would map `total_amount` back to `amount_usd`.

## Did the fix work?

Not tested.

## Reproduce

```bash
python3 runner/run_cases.py --source-mode fixed --cases 02-schema-rename-column
# Reconnect the source, check the preview shows total_amount, press Enter, then run.
python3 data-validation/validate.py 02-schema-rename-column
```

## Validator

| Run | Verdict | Why |
|---|---|---|
| 1 | ⏹ STOPPED | No output; stopped on `'amount_usd'` |

## Evidence

- [failure-log.json](evidence/02-schema-rename-column/failure-log.json), [failure-notification.txt](evidence/02-schema-rename-column/failure-notification.txt)
- Run record: `results/runs.csv`
