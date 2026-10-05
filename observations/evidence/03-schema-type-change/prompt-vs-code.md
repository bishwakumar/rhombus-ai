# Case 03 – the prompt changes, the code doesn't

Two successful case 03 runs, on different prompt versions, compared directly from the saved Rhombus logs:

| | [Earlier run](rhombus-log-earlier-prompt-v1.json) | [Run 4](rhombus-log-run4-prompt-v2.json) |
|---|---|---|
| Prompt | "Clean this orders dataset. … IMPORTANT: Some input datasets may be missing one or more of these columns … add any missing expected columns as empty string columns …" | "Clean this orders dataset (v2). … STEP 0 — MISSING COLUMNS GUARD (run this first) … FINAL STEP — force text dtype before output …" |
| Code (`params.code`) | Original code | **Character-for-character identical** to the earlier run |
| Code contains the missing-column guard? | No | No |
| Code contains the force-text final step? | No | No |
| Metrics | 470 rows, 1,745 cells modified | 470 rows, 1,745 cells modified |

Both prompts were written by the chatbot as "fixes" (case 01, then case 05). Neither changed the code that runs. The chatbot itself later said: "The pipeline was executing old cached code from before the missing-column fix was added" (case 05 reply).
