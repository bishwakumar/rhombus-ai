# Answer key (seed 2026)

- Source rows: **500**
- Unique orders: **470**
- Expected cleaned rows: **470** (see `00-baseline.expected.csv`)
- True order dates: Jan 1 to Mar 12, 2026, day of month always 1-12. Slash and dash dates are month first.
- Valid amounts: $11.87 to $1,998.49

## Planted defects (counted on unique rows, plus duplicates)

| Column | Problem | Rows |
|---|---|---|
| amount_usd | $ and commas ($1,540.73) | 125 |
| amount_usd | '$ ' prefix ($ 403.03) | 42 |
| amount_usd | USD suffix (403.03 USD) | 36 |
| amount_usd | fewer than 2 decimals (403.5, 120) | 43 |
| amount_usd | missing | 11 |
| amount_usd | negative | 14 |
| amount_usd | non-numeric (abc, N/A, free, TBC) | 20 |
| country | abbreviation / variant (AU, USA, GB) | 391 |
| country | missing | 11 |
| customer_name | ALL CAPS | 130 |
| customer_name | all lower case | 71 |
| customer_name | leading/trailing spaces | 23 |
| customer_name | missing | 17 |
| customer_name | mixed case (PRIYA khan) | 41 |
| duplicate | exact copy of the previous row | 20 |
| duplicate | same order_id as previous row, different amount/status | 10 |
| email | UPPER CASE | 73 |
| email | invalid format | 34 |
| email | missing | 32 |
| email | placeholder (n/a, none, -) | 21 |
| order_date | MM-DD-YYYY | 36 |
| order_date | MM/DD/YYYY | 240 |
| order_date | already ISO (YYYY-MM-DD) | 64 |
| order_date | invalid (13/45/2026, TBD, 2026-02-30) | 16 |
| order_date | missing | 25 |
| order_date | text (March 4 2026) | 89 |
| quantity | decimal like 2.0 | 33 |
| quantity | fraction like 1.5 | 10 |
| quantity | missing | 26 |
| quantity | number word (three) | 44 |
| quantity | zero or negative | 29 |
| status | Capitalised | 79 |
| status | UPPER CASE | 116 |
| status | invalid (xyz, ??, 1, unknown) | 17 |
| status | trailing spaces | 22 |

## Drift details

- 03-schema-type-change: 43 rows with missing/invalid dates are blank (a timestamp column can't hold 'TBD').
- 06-semantic-cents: valid amounts become 1,187 to 199,849 (cents).
- 07-semantic-date-swap: 297 slash/dash dates swapped to day first; all still valid dates. Parsed months spread across Jan-Dec instead of Jan-Mar.
