# 03 – Schema drift: change a data type

| | |
|---|---|
| **Input** | [`datasets/03-schema-type-change.csv`](../datasets/03-schema-type-change.csv): 500 rows, 8 columns |
| **Date** | 5 Oct 2026, AEDT |
| **Did Rhombus pass it?** | ✅ Yes |
| **Should it have?** | ❌ **No**: every date came out blank |
| **Pipeline stopped?** | No |
| **Chatbot fix worked?** | ⚠️ Yes after a hint; input not confirmed (see below) |
| **Severity** | **High** |

## What I changed

`order_date` changed from text dates (`03/09/2026`, `March 8 2026`) to Unix timestamps (e.g. `1773014400`). Missing or invalid dates left blank.

## What I expected

The code only knows text date formats, so the run should **succeed** with every `order_date` **blank** and no warning.

## What happened

| Run | Result |
|---|---|
| 3 (11:49:06) | **Completed successfully.** Every `order_date` blank |
| 4 (rerun) | **Completed successfully.** Byte-identical to run 3 |

- `order_date` is **100% blank** (baseline: 8.7%). All other columns correct.
- **No warning anywhere.** Only the independent validator caught it.
- The same result appears in an earlier run on 4 Oct, under a different prompt version (same metrics).

Runs 1, 2 and 5 were setup attempts and aren't used. Run 3's output was missed by the runner and attached with `--attach` (noted in `runs.csv`).

## What the logs said

From [rhombus-log-run4-prompt-v2.json](evidence/03-schema-type-change/rhombus-log-run4-prompt-v2.json):

```
"status": "success",
"metrics": { "modified_cell_count": 1745, "affected_row_count": 470,
             "output_row_count": 470, "records_processed": 470, "output_column_count": 8 }
```

- **Reports success.** Nothing hints at a problem.
- **"1,745 cells modified" includes the 470 dates that were wiped.** Erasing data counts the same as cleaning it.
- **The prompt and the code disagree.** The prompt says *"STEP 0 — MISSING COLUMNS GUARD (run this first)"* and *"FINAL STEP — force text dtype before output"*; the code contains neither. The earlier run's log ([rhombus-log-earlier-prompt-v1.json](evidence/03-schema-type-change/rhombus-log-earlier-prompt-v1.json)) has a **different** prompt and **character-for-character the same** code: [prompt-vs-code.md](evidence/03-schema-type-change/prompt-vs-code.md).

## What the chatbot said

Full replies and checks: [chatbot-reply.md](evidence/03-schema-type-change/chatbot-reply.md).

**Reply 1**, asked *"The latest output has every order_date empty. Why?"*:
> **Root cause:** The current `orders` source (`_07_semantic_date_swap`) uses **DD/MM/YYYY** … a date like `15/03/2026` … failed the month-first parse and went blank.
- ❌ Answered about **a different dataset**; never mentioned timestamps.
- ❌ `15/03/2026` doesn't exist in either file, and the 07 swap is described backwards.
- ❌ Its "v3" fix (day-first after month-first) fixes neither case. Applied without asking.

**Reply 2**:
> `_03_schema_type_change` stores `order_date` as **Unix epoch timestamps** (e.g. `1773014400.0` = 16 Jan 2026) … converts it using `pd.Timestamp(float(val), unit='s')`
- ✅ Correct cause and method.
- ❌ Wrong example: `1773014400` is **9 March 2026** (order 10001).
- ❌ "v4" applied without asking.

**Reply 3**: said the pipeline *"can't run right now because the input source … has gone stale"*. A run had already completed by then.

## Did the fix work?

**The output says yes; the input isn't confirmed.**

After v4, run 6 has **every date correct** ([run6-output-head.txt](evidence/03-schema-type-change/run6-output-head.txt): `1773014400` → `2026-03-09`). Validator: ✔ PASS (with warnings).

But case 03 holds the same orders as the baseline, so a correct output is **byte-identical to the baseline output**, and stale baseline data would produce the same file. The input preview wasn't captured at that run, and the chatbot itself said the source had gone stale. **So this can't be proven either way; it's listed as a limitation.**

Quantities are still `1.0` and amounts still `456.8` in run 6, although the prompt says *"never 5.0"* and *"force text dtype"*.

## Reproduce

```bash
python3 runner/run_cases.py --cases 03-schema-type-change
# Press Enter, then select _03_schema_type_change (preview shows numbers like 1773014400).
python3 data-validation/validate.py 03-schema-type-change
```

## Validator

| Run | Verdict | Why |
|---|---|---|
| 3, 4 | ✘ FAIL | `order_date` 100% blank; 429 dates wrong; runs byte-identical |
| 6 (after fix) | ✔ PASS (with warnings) | Every value correct; identical to baseline (could also mean stale input); formatting |

## Not captured

Input preview screenshot; Rhombus log for run 6.
