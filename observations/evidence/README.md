# Evidence

Everything the observation files link to. Times: AEST (UTC+10) on 3 Oct, AEDT (UTC+11) from 4 Oct. The account email is redacted where it appeared.

## 00-baseline/ (3 Oct, pipeline build)
| File | Proves |
|---|---|
| `canvas-no-cleaning-step.png` | The pipeline had only Data Input → Data Output when the chatbot said all rules were applied |
| `chatbot-claim-all-rules-applied.md` | The chatbot's "All rules are applied correctly" reply |
| `first-dataset/output_1_no_cleaning_step.csv` | That pipeline's output: 283 rows, uncleaned, dates converted by the platform |
| `first-dataset/output_2…4_*.csv`, `md5.txt` | After two formatting-fix requests, outputs stayed byte-identical |
| `first-dataset/rhombus_cleaning_scorecard.xlsx` | Cell-by-cell check of the first cleaned output |

## scheduler/ (3 Oct)
| File | Proves |
|---|---|
| `logs-and-three-active-schedules.png` | Three Active schedules, blank "Next run", no scheduled runs in the log |
| `schedule-active-next-run-blank.png`, `schedule-active-next-run-countdown.png` | `*/2` never had a next run; `*/5` counted down, then went blank |
| `create-schedule-dialog.png` | The schedule options and the failure-notification setting |
| `execution-log-2026-10-03.txt`, `schedule-list-2026-10-03.txt` | The log and schedule list as text |
| `rhombus_scheduler_evidence.xlsx` | 74 expected runs vs 0 actual |

## s3-connection/ (3 Oct)
| File | Proves |
|---|---|
| `s3-error-and-checks.md` | The error, the generated policy that was applied, and every check made |
| `s3-connection-form.png`, `s3-connection-optional-settings.png` | The connection form and generated-policy step |

## 01-schema-drop-column/ (4 Oct)
| File | Proves |
|---|---|
| `gcs-source-listing.txt` | The new file (28.2 KB) was in the bucket at 14:48:52 |
| `input-preview-stale.png` | Rhombus still showed the old file, with `email` |
| `stale-output-md5.txt` | The run's output was byte-identical to the baseline output |
| `failure-log.json`, `failure-notification.png` | After a reconnect, the run stopped on `'email'` |
| `chatbot-reply.md` | The chatbot's diagnosis and claimed fix |

## 02-schema-rename-column/ (4 Oct)
| File | Proves |
|---|---|
| `failure-log.json`, `failure-notification.txt` | The run stopped on `'amount_usd'` at 17:06:23 |

## 03-schema-type-change/ (5 Oct)
| File | Proves |
|---|---|
| `rhombus-log-run4-prompt-v2.json` | Run 4: "success", 1,745 cells modified, every date blank |
| `rhombus-log-earlier-prompt-v1.json` | An earlier run: different prompt, identical code, same result |
| `prompt-vs-code.md` | The two prompts differ; the code is character-for-character the same |
| `chatbot-reply.md` | All chatbot replies, checked against the data |
| `chatbot-says-code-not-updated.png` | 15:43: the chatbot finds the last-executed code has no epoch support, after saying the fix was in place |
| `chatbot-v6-patching-code.png` | 15:44: "v6"; the chatbot patches the code directly after tool errors |
| `output-1524-dates-still-blank.png` | An output at 15:24:33 still had every date blank |
| `run6-output-head.txt` | Run 6 has correct dates |
| `timeline.md` | The order of events, and the one open question about run 6 |

## 05-schema-combined/ (5 Oct)
| File | Proves |
|---|---|
| `run1-error.txt` | Stopped on `'email'` at 12:08 |
| `chatbot-reply.md` | The "v2 forces regeneration" claim |
| `run3-error.txt` | After the fix: still `code_sha=3ca80b148200`, still `'email'` |

## platform/ (5 Oct)
| File | Proves |
|---|---|
| `selecting-dataset-starts-run.png`, `run-on-metadata-table-failed.png` | Selecting a dataset starts a run by itself; the run on `log` failed |
| `dataset-picker-placeholder-names.png`, `dataset-picker-names.txt` | Ten datasets all shown as `placeholder_file`; their real names are sync-metadata tables |
| `single-gcs-connection.png` | Only one GCS connection possible |
| `rhombus-notifications-2026-10-05.txt` | Bursts of runs, failures also logged as successes, old `code_sha` after the "fix", internal details in errors |
| `gcs-target-listing-2026-10-04.txt`, `gcs-target-listing-2026-10-05.txt` | Outputs from runs nobody started; 32 outputs for about 15 intended runs; case 07 MD5s |

## ui-tests/ (5 Oct)
| File | Proves |
|---|---|
| `manual-run-report.png` | The manual-run test passed every step, including a new file in GCS with the cleaned header |
| `s3-test-report.png` | The S3 test stopped on a locator (older file version), so F8 isn't yet confirmed by this test |
| `run-summary.txt` | Results of the UI test runs |

## api-tests/ (5 Oct)
| File | Proves |
|---|---|
| `run-output.txt` | 13 pass, 0 fail, 3 known issues against the live API |
| `responses.md` | The API responses behind F1, F9, F10, F15, F30 and the chat-artifact evidence |

## Not captured
Input previews for cases 03, 04, 06 and 07; the Rhombus log entries for case 04 and for case 03 run 6.
