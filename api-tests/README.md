# API tests

Tests that call the Rhombus backend directly, using the same requests the web app makes (found in the browser's Network tab). They assert on **status codes and response contents**.

No dependencies: Node.js 20+ built-in test runner and `fetch`.

## Setup

```bash
cd api-tests
cp .env.example .env
```

Put your access token in `.env` as `RHOMBUS_TOKEN`. To get it: while logged in to Rhombus, open `https://rhombusai.com/api/auth/session` in the browser and copy the value of `accessToken` (without quotes). The web app sends this token to the API as `Authorization: Bearer <token>`.

`.env` is git-ignored. **Never commit or share the token.** It expires; when the positive tests start returning 401, copy a fresh one.

## Run

```bash
npm test
```

Output is grouped into **positive**, **negative (security)** and **known issues**, and every test prints one `ℹ` line with what it found (for example `refused with 401`, or the stored data types). A clean run ends with `pass 16`, `fail 0`.

**Known issues are confirmed, not skipped.** Each known-issue test checks that the bug is **still present**, so it passes while the bug exists. If Rhombus fixes it, the test fails with a message saying the issue appears fixed, the signal to update the finding and the test.

## Endpoints

| Endpoint | Used by the app for |
|---|---|
| `GET /api/dataset/projects/{id}/context` | The project's organisation and the caller's roles |
| `GET /api/dataset/analyzer/v2/projects/{id}/nodes` | The full pipeline: nodes, connections, generated code, destination, last-run columns and types |
| `GET /api/dataset/analyzer/v2/projects/{id}/datasets` | The project's datasets, including where their snapshot is stored |
| `GET /api/dataset/analyzer/v2/projects/{id}/datasets/{datasetId}/preview?offset=&limit=` | Rows, column types and row count of a dataset |
| `GET /api/dataset/analyzer/v2/projects/{id}/chat/artifacts` | Files the AI Builder created in its own workspace |

## Tests

| Test | Type | Asserts |
|---|---|---|
| Project context returns this project and the caller's roles | Positive | `200`; `id` matches; `organization_id` is a number; roles are known values; response under 5 s |
| Pipeline nodes: Data Input → AI cleaning step → output, connected in order | Positive | `200`; one input, one `llm` and one output node; the AI step holds generated code; edges input → llm → output. Each check reports what it found when it fails |
| F30: output node has lost its GCS destination settings | Known issue (confirmed) | The output node has no `format_type` or `destination_id` (on 5 Oct the API returned only `{org_id, user_id}`) |
| Pipeline nodes: last run kept the 8 cleaned columns | Positive | `lastRunColumns` equals the 8 expected columns |
| F10: amount_usd and quantity stored as numbers | Known issue (confirmed) | The code converts both columns to text (`.astype(str)`), yet the platform stores them as `float64` |
| Datasets: every dataset belongs to this project | Positive | `200`; each dataset has a numeric `id`, a `title`, and this `project_id` |
| Datasets: no credential fields exposed with values | Positive (security) | `client_id` / `client_secret` fields are present in the response but must be empty |
| Dataset preview: respects the limit, describes every column | Positive | `limit=5` returns at most 5 rows; every column has a dtype and semantic type; every row has exactly those columns |
| Chat artifacts: paths inside `rhombus_output`, with sizes | Positive | Every artifact path starts with `rhombus_output/`; `artifact_paths` agrees with the list |
| F15: datasets named `placeholder_file` | Known issue (confirmed) | At least one dataset's `file` field is `"placeholder_file"` |
| Project context without a login is refused | **Negative** | `401`/`403` from the API (JSON body); no project data in the response |
| Project context with an invalid token is refused | **Negative** | `401`/`403` from the API; no project data |
| Pipeline nodes without a login are refused | **Negative** | `401`/`403` from the API; no pipeline code in the response |
| A project you don't belong to is refused | **Negative** | `403`/`404` from the API; no other project's data |
| Dataset list without a login is refused | **Negative** | `401`/`403` from the API; no storage locations in the response |
| Dataset preview without a login is refused | **Negative** | `401`/`403` from the API; no rows in the response |

### Why refusals must be JSON

A `403` can also come from a proxy or network filter in front of the API. While writing these tests, a sandbox network filter answered every request with `403 Host not in allowlist`, and status-only checks passed. The negative tests therefore also require a JSON body from the API itself, so a refusal is only counted when it really comes from Rhombus.

### Access-control test

The "project you don't belong to" test sends **one** request and only expects a refusal. If it ever returned data, that would be a security issue to report privately to Rhombus, not to publish.
