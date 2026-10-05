# API responses (excerpts), 5 Oct 2026

Captured from the browser's Network tab while logged in. Personal details and tokens removed.

## GET /api/dataset/projects/5248/context
```json
{ "id": 5248, "organization_id": 666, "org_role": "admin", "project_role": "admin" }
```

## GET /api/dataset/analyzer/v2/projects/5248/nodes (afternoon)
- Input node: `description: "_03_schema_type_change"`, `transformationParams.dataset_id: 514840811`, `sample_size: 100000`, `sampling_enabled: true`.
- AI node (`llm_node_1`, tag `clean_orders`): `prompt: "Clean orders v6"`, `mode: "code"`. The **code** now contains the missing-column step and Unix timestamp handling (`pd.Timestamp(epoch, unit="s")`), and ends by converting `amount_usd` and `quantity` to text (`.astype(str)`).
- Same node, last run: `lastRunColumns` = the 8 cleaned columns; `lastRunDtypes` = `int64, object, object, object, float64, float64, object, object`, so **`amount_usd` and `quantity` are stored as `float64`** despite the code's text conversion (F10).
- Output node: `description: "Export to rhombus-target (csv)"`, `transformationParams: { org_id, node_id, user_id, project_id: 5248, format_type: "csv", destination_id: 56, download_local: false }`.

## Same endpoint (evening)
- Output node `transformationParams`: `{ "org_id": 666, "user_id": 662 }` only (F30).

## GET /api/dataset/analyzer/v2/projects/5248/datasets
```json
{ "id": 3258990920, "title": "orders", "file": "placeholder_file", "file_size": "17804",
  "client_id": "", "client_secret": "", "project_id": 5248,
  "data_array": "[{\"key\": \"projects/5248/rhombussource/rhombussource/orders/data/…_2026-10-05T04-50-54Z.parquet\", \"size_bytes\": 17804}]" }
```
- `file` is literally `"placeholder_file"` (F15).
- The data is a **parquet snapshot** taken at sync time (04:50:54 UTC), not the live GCS file (explains F1).

## GET /api/dataset/analyzer/v2/projects/5248/datasets/3258990920/preview?offset=0&limit=20
- `num_rows: 500`; `dtypes.order_date: "datetime64[ns]"` (dates already converted on input, F9); includes `discount_code`, so the "orders" dataset currently holds the case 04 file.

## GET /api/dataset/analyzer/v2/projects/5248/chat/artifacts
| File | Time |
|---|---|
| `rhombus_output/probe.py`, `clean.py`, `v0_baseline_cleaned.csv` | 3 Oct 14:12–14:13 AEST (the one-off cleaned file from the build stage) |
| `rhombus_output/probe_orders.py` | 4 Oct 15:17 AEDT |
| `rhombus_output/probe_dates.py`, `probe_dates2.py`, `probe_03.py` | 5 Oct 15:33–15:39 AEDT (while investigating case 03, just before the 15:43 "last-executed code doesn't have Unix epoch support" reply) |
