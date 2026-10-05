# 06 – Semantic drift: dollars become cents

| | |
|---|---|
| **Input** | [`datasets/06-semantic-cents.csv`](../datasets/06-semantic-cents.csv): 500 rows, 8 columns |
| **Date** | 5 Oct 2026, AEDT |
| **Did Rhombus pass it?** | ✅ Yes |
| **Should it have?** | ❌ **No**: amounts are 100× too high |
| **Did Rhombus notice?** | No |
| **Did our validation catch it?** | ✅ Yes |
| **Severity** | **High** |

## What I changed

Every `amount_usd` value written in **cents**, in the same column and the same format: `$ 1297.92` → `$ 129792`, `$1,361.98` → `$136,198`. The structure is unchanged.

## What I expected

Nothing structural changes, so the run should **succeed** and deliver amounts 100× too high, **with no warning**.

## What happened

- The run **completed successfully**: 470 rows, 1,534 cells modified (13:21:49, and again 13:22:30).
- One dataset selection produced **two outputs** (13:21:48 and 13:22:29).
- **Every amount is 100× too high**: the largest is **199,849.00** instead of 1,998.49.
- Everything else (rows, schema, names, dates, statuses) is correct.

Evidence: [notifications](evidence/platform/rhombus-notifications-2026-10-05.txt) (13:21–13:22), [bucket listing](evidence/platform/gcs-target-listing-2026-10-05.txt).

## What the logs said

```
01:21:49 PM  Applied transformation: Custom: … Impact: 470 row(s) affected, 1534 cell(s) modified.
01:21:49 PM  Pipeline completed successfully
```

Success, no warning. The rules were applied exactly as written; nothing hints that the amounts changed meaning.

## Does Rhombus notice?

**No.**

## Does our validation catch it?

**Yes.** Schema, row counts, blank rates and rule compliance all pass, as any structural check would. Two checks catch it:
- **Range:** 423 of 425 amounts above $2,500 (the baseline never exceeds $2,000). The 2 not flagged are orders under $25, which stay below 2,500 even in cents.
- **Correctness** (against the known right answer): all 425 amounts wrong.

## What the chatbot said

Not tested. *(A good answer would ask whether the source now uses cents before changing anything.)*

## Reproduce

```bash
python3 runner/run_cases.py --cases 06-semantic-cents
# Press Enter, then select _06_semantic_cents (amounts have no decimals, e.g. 129792).
python3 data-validation/validate.py 06-semantic-cents
```

## Validator

| Run | Verdict | Why |
|---|---|---|
| 1 | ✘ FAIL | 423 of 425 amounts above $2,500 (max 199,849.00); all 425 amounts wrong |

## Not captured

Input preview screenshot.
