# 07 – Semantic drift: month/day becomes day/month

| | |
|---|---|
| **Input** | [`datasets/07-semantic-date-swap.csv`](../datasets/07-semantic-date-swap.csv): 500 rows, 8 columns |
| **Date** | 5 Oct 2026, AEDT |
| **Did Rhombus pass it?** | ✅ Yes |
| **Should it have?** | ❌ **No**: 252 dates are wrong |
| **Did Rhombus notice?** | No |
| **Did our validation catch it?** | ✅ Mostly: 208 of 252 (the rest can't be seen in the output) |
| **Severity** | **High** |

## What I changed

202 slash and dash dates rewritten day-first: `03/09/2026` (9 March) became `09/03/2026`. Every true day is 1–12, so **every swapped date is still a valid date**. The structure is unchanged.

## What I expected

The code reads slash dates month-first, so `09/03/2026` becomes 3 September. The run should **succeed with no warning**.

## What happened

- Three successful runs (13:32:11, 13:32:46, 13:38:53), all **byte-identical** (MD5 `0d0c4719…`).
- Rhombus: 466 rows, 1,316 cells modified, no warning.
- **252 of the 470 order dates changed meaning:**

| | Dates |
|---|---|
| Now outside the real January–March range (all 12 months appear) | **208**, of which **42 are in the future** |
| Swapped into another valid January–March date (e.g. 3 Jan → 1 Mar) | **44** |

Run 1 was first recorded as producing no output; Rhombus's notification log and the bucket showed it had succeeded, so the record was corrected with `--attach`.

Evidence: [notifications](evidence/platform/rhombus-notifications-2026-10-05.txt) (13:32, 13:38), [bucket listing and MD5s](evidence/platform/gcs-target-listing-2026-10-05.txt).

## What the logs said

```
01:38:54 PM  Applied transformation: Custom: … Impact: 466 row(s) affected, 1316 cell(s) modified.
01:38:54 PM  Pipeline completed successfully
```

Success, no warning.

## Does Rhombus notice?

**No.** The Data Input node also converts dates by itself before the cleaning code runs, so the misreading happens before any rule could check it.

## Does our validation catch it?

**Mostly.**
- **Range check:** 208 dates outside January–March; every month appears. Flagged.
- **The other 44 can't be detected from the output.** They're wrong but plausible. Only an agreed date format at the source would prevent them.
- The correctness check counts all 252, because in this test the right answer is known; in real use it wouldn't be.

## What the chatbot said

Not asked about this case directly. During the case 03 test it described this dataset unprompted, **reversed the swap** in its explanation, and proposed trying day-first only after month-first, which can't fix it, since every swapped date is also valid month-first ([case 03 replies](evidence/03-schema-type-change/chatbot-reply.md)). *(A good answer would ask which date format the source uses.)*

## Reproduce

```bash
python3 runner/run_cases.py --cases 07-semantic-date-swap
# Press Enter, then select _07_semantic_date_swap (order 10001 shows 09/03/2026).
python3 data-validation/validate.py 07-semantic-date-swap
```

## Validator

| Run | Verdict | Why |
|---|---|---|
| 1, 2 | ✘ FAIL | 208 of 429 dates outside Jan–Mar (months 1–12); 252 dates wrong; runs byte-identical |

## Not captured

Input preview screenshot.
