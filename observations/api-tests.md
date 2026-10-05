# API tests

| | |
|---|---|
| **Code** | [`api-tests/`](../api-tests/) |
| **Date** | 5 Oct 2026, AEDT |
| **Result** | 16 tests: 13 pass, 0 fail, 3 known issues (F10, F15, F30) |

## What I tested

Five backend endpoints the web app uses, found in the browser's Network tab, called directly with Node's `fetch`. Every test asserts on the status code **and** the response contents.

| Endpoint | Purpose |
|---|---|
| `GET /api/dataset/projects/{id}/context` | Project and the caller's roles |
| `GET /api/dataset/analyzer/v2/projects/{id}/nodes` | The full pipeline definition |
| `GET /api/dataset/analyzer/v2/projects/{id}/datasets` | The project's datasets |
| `GET …/datasets/{datasetId}/preview` | A dataset's rows and column types |
| `GET …/chat/artifacts` | Files in the AI Builder's own workspace |

## What I expected

- Logged-in requests return the project's data in a consistent shape.
- Requests without a valid login, or for another customer's project, are refused, with no data in the response.

## What happened

**All 6 negative tests pass.** Missing login, invalid token and another customer's project are all refused with a proper API error, and no project data, pipeline code, storage locations or rows appear in the refusals.

**The API confirmed or explained several findings:**

| Finding | What the API showed |
|---|---|
| **F30 (new)** | The output node's settings are only `{"org_id": 666, "user_id": 662}`. Earlier the same day they included `format_type: "csv"`, `destination_id: 56` and `project_id`. The destination configuration disappeared (likely linked to F28). Not yet confirmed in the UI |
| **F10 (root cause)** | The code ends with `.astype(str)` for `amount_usd` and `quantity`, yet the platform records them as `float64`. The platform re-types the data after the code, so the formatting can't be fixed through the AI-generated code |
| **F15 (explained)** | Every dataset's `file` field is literally `"placeholder_file"` |
| **F1 (explained)** | Pipelines read a **parquet snapshot** taken when the source syncs (`…_2026-10-05T04-50-54Z.parquet`), not the live GCS file. A changed file is ignored until the next sync |
| **F9 (confirmed)** | The dataset preview types `order_date` as `datetime64` before any cleaning |
| **F5 (resolved for case 03)** | The stored code now contains the Unix timestamp handling: the chatbot's sixth attempt ("v6"), patching the code directly, finally reached the running code |
| **Build stage (confirmed)** | The AI Builder's workspace still holds `v0_baseline_cleaned.csv` from 3 Oct 14:13: the one-off file it produced when it claimed "All rules are applied correctly" |

**Security observation:** the datasets response includes `client_id` and `client_secret` fields. They're empty, and a test checks they stay empty, but credential fields shouldn't be part of this response at all.

## Problems met while writing the tests

- **I initially asserted fields from an earlier response** (`project_id` on every node). The pipeline definition had changed since, so the checks were wrong; they were removed, and every remaining check reports what it found when it fails.
- **Status codes alone aren't enough.** While developing, a network filter answered every request with `403 Host not in allowlist`, and status-only negative tests passed. The negative tests now also require a JSON body from the API.

## Evidence

- [Test run output](evidence/api-tests/run-output.txt)
- [API responses (excerpts)](evidence/api-tests/responses.md)

## Reproduce

```bash
cd api-tests
cp .env.example .env     # add RHOMBUS_TOKEN (accessToken from https://rhombusai.com/api/auth/session)
npm test
```
