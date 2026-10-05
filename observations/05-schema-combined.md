# 05 – Schema drift: all changes together

| | |
|---|---|
| **Input** | [`datasets/05-schema-combined.csv`](../datasets/05-schema-combined.csv): 500 rows, 8 columns |
| **Date** | 5 Oct 2026, AEDT |
| **Did Rhombus pass it?** | ❌ Stopped |
| **Should it have?** | No. Stopping is right, but only the first of four problems was reported |
| **Pipeline stopped?** | ✅ Yes |
| **Chatbot fix worked?** | ❌ No. Claimed to force new code; nothing changed |
| **Severity** | **High** |

## What I changed

All four schema changes at once: `email` removed, `amount_usd` renamed to `total_amount`, `order_date` as Unix timestamps, and a new `discount_code` column.

## What I expected

A stop on `'email'`, the first missing column the code reaches.

## What happened

| Run | Time | Result | Evidence |
|---|---|---|---|
| 1 | 12:08 | **Stopped** on `'email'`, `code_sha=3ca80b148200` | [run1-error.txt](evidence/05-schema-combined/run1-error.txt) |
| 3 (after the chatbot fix) | 13:04:17, 13:04:29, 13:04:35 | **Stopped three times in 18 s**, same error, **same `code_sha`** | [run3-error.txt](evidence/05-schema-combined/run3-error.txt), [notifications](evidence/platform/rhombus-notifications-2026-10-05.txt) |

Nothing was written to GCS. Run 2 was stopped by hand and isn't used.

## What the logs said

```
Pipeline failed at clean_orders: LLM execution failed (code_sha=3ca80b148200): 'email' --- Generated code --- …
```

Same weaknesses as [case 01](01-schema-drop-column.md#what-the-logs-said), plus:
- ❌ **Only the first problem is reported.** Four things changed. A customer who fixed `email` would next hit `amount_usd`, and would never be told about the timestamp dates or the dropped `discount_code`, because those don't cause errors.
- ❌ Each failure is accompanied by *"Pipeline execution completed successfully."* at the same second.

## What the chatbot said

"Ask Chatbot" on the error, nothing added. Full reply: [chatbot-reply.md](evidence/05-schema-combined/chatbot-reply.md).

> The `clean_orders` node has been updated on the canvas with a refreshed prompt (labelled v2), which forces the pipeline to regenerate fresh code rather than use the stale cached version (`3ca80b148200`). **What happened:** The pipeline was executing old cached code from before the missing-column fix was added.

- ⚠️ **Diagnosis incomplete:** only `'email'`. Nothing about the rename, the timestamps or the new column.
- ✅ **Correctly admitted** the earlier case 01 fix never reached the running code.
- ❌ **Claimed** the new prompt "forces the pipeline to regenerate fresh code".
- ❌ Changed the pipeline without asking.

## Did the fix work?

**No.** The three runs at 13:04 still used `code_sha=3ca80b148200` and still stopped on `'email'`.

Had it worked, the fix (blank any missing column) would have produced every amount blank (rename ignored), every date blank (timestamps unparsed) and `discount_code` dropped, all reported as success.

## Reproduce

```bash
python3 runner/run_cases.py --cases 05-schema-combined
# Press Enter, then select _05_schema_combined (no email; has total_amount and discount_code).
python3 data-validation/validate.py 05-schema-combined
```

## Validator

| Run | Verdict | Why |
|---|---|---|
| 1, 3 | ⏹ STOPPED | No output; stopped on `'email'` (error recorded in `runs.csv`) |
