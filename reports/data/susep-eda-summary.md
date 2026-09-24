# P1-SUSEP-01 — EDA streaming của nguồn SUSEP

Raw CSV chỉ được đọc tuần tự; không bị sửa. Duplicate và candidate-grain uniqueness dùng SQLite tạm ngoài repository.

## Schema và quy mô

- Rows: **8,338,214**
- Columns: **8**
- Source bytes: **751,126,569**
- Elapsed seconds: **3466.546**

## Field evidence

| Field | Source type | Null | Invalid | Cardinality or range | SQL target |
|---|---|---:|---:|---|---|
| company_code | integer-like text | 0 | 0 | cardinality 196 | INT |
| company_name | text | 0 | 0 | cardinality 196 | NVARCHAR(116) |
| year_month | ISO date text | 0 | 0 | 2003-01-01 to 2023-07-01 | DATE |
| product | text | 0 | 0 | cardinality 144 | NVARCHAR(42) |
| state | text | 0 | 0 | cardinality 40 | NVARCHAR(2) |
| premiums | decimal text | 0 | 0 | -224022539.61 to 2598854052.42 | DECIMAL(38,29) |
| claims | decimal text | 0 | 0 | -4162417826.88 to 5323648483.83 | DECIMAL(38,29) |
| claim_premium_ratio | decimal text or null sentinel | 5,167,094 | 0 | -6590560657819567 to 19804447419966428 | DECIMAL(35,18) |

## Duplicate và grain

- Exact duplicate rows: **0**.
- Candidate key: company_code, year_month, product, state.
- Candidate-key duplicate groups / excess rows: **0 / 0**.
- Kết luận: Mỗi source row là một unique market observation theo company/month/product/state.

## Ranh giới semantic

SUSEP schema có company, month, product, state, premium, claims và ratio nguồn cung cấp. Nó không có customer, policy, VIN, exposure hay claim-event identifier.
