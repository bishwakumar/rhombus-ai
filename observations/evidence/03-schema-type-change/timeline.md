# Case 03 – timeline of the fix attempts (5 Oct 2026, AEDT)

| Time | Event | Evidence |
|---|---|---|
| 11:49:06 | Run 3: success, every `order_date` blank | `outputs/03-schema-type-change__run3.csv` |
| (rerun) | Run 4: success, byte-identical to run 3 | [rhombus-log-run4-prompt-v2.json](rhombus-log-run4-prompt-v2.json) |
| afternoon | Chatbot reply 1: diagnoses the wrong dataset; "v3" applied | [chatbot-reply.md](chatbot-reply.md) |
| afternoon | Chatbot reply 2: correct cause (timestamps); "v4" applied | [chatbot-reply.md](chatbot-reply.md) |
| afternoon | Chatbot reply 3: "fix is in place", source "has gone stale" | [chatbot-reply.md](chatbot-reply.md) |
| 15:24:33 | Output `RhombusAI_output_1791174273460.csv`: dates **still blank** | [output-1524-dates-still-blank.png](output-1524-dates-still-blank.png) |
| 15:43 | Chatbot: "The last-executed code doesn't have Unix epoch support … I need to patch the stored code directly" | [chatbot-says-code-not-updated.png](chatbot-says-code-not-updated.png) |
| 15:44 | Chatbot patches the code field directly ("Clean orders v6") after tool errors | [chatbot-v6-patching-code.png](chatbot-v6-patching-code.png) |
| ? | Run 6: every date correct, byte-identical to the baseline output | [run6-output-head.txt](run6-output-head.txt) |

**Open question:** whether run 6 came **after** the 15:44 direct code patch (then the fix worked, on the sixth attempt) or before it (then run 6 most likely read stale baseline data, since the code had no epoch support). The run 6 row in `results/runs.csv` (`triggered_at`, `rhombus_output_file`) answers this.
