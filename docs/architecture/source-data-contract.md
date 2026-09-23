# Source Data Contract — brvehins1

Trạng thái: `DONE` cho snapshot canonical được profile ngày 2026-09-22. Contract này là nguồn sự thật cho bootstrap SQL, staging, DWH và Data Quality foundation.

## 1. Ranh giới và raw immutability

- Canonical input chỉ là năm file `brvehins1a.csv` đến `brvehins1e.csv` trong `data/raw/brvehins1/`.
- Mỗi file có 393,071 dòng dữ liệu sau header; tổng 1,965,355 dòng; 23 cột theo dictionary.
- Raw là immutable: không sửa CSV, không ghi output vào `data/raw/`, không deduplicate raw và không đưa raw vào Git.
- `data/raw/susep.gov.br/insurance_dataset.csv` là **LEGACY / NON-CANONICAL**, không được ingest, join hoặc dùng làm fallback.
- Precision SQL phải preserve raw lexical value, không chỉ dtype `float64`: `ExposTotal` dùng `DECIMAL(21,17)` và `PremTotal` dùng `DECIMAL(34,27)` theo `reports/data/brvehins1-numeric-precision.json`; các mapping còn lại nằm ở dictionary.

## 2. Grain đã đóng băng

Một dòng canonical là **một source-delivered aggregate risk observation**: nó chứa các descriptor người lái, xe và địa lý cùng các measure exposure, premium, sum insured, claim count và claim amount. Nguồn không có timestamp, transaction key, business customer identifier hay business policy identifier.

Vì vậy fact không được mô tả như một policy cá thể, một customer cá thể hay một event claim đơn lẻ. Grain kho dữ liệu sẽ là **một staging source row được lineage về partition và row ordinal**, giữ nguyên các measure nguồn.

## 3. Technical identity và duplicate policy

| Thành phần | Chính sách |
|---|---|
| `SourceFile` | Tên một trong năm partition canonical. |
| `SourceRowNumber` | Ordinal 1-based của dòng dữ liệu trong file, không tính header. |
| `BatchId` | Khóa kỹ thuật của một lần ingest partition. |
| `SourceRecordHash` | SHA-256 của canonical serialization các trường nguồn, dùng làm fingerprint/audit, không là identity duy nhất. |
| Uniqueness kỹ thuật | `SourceFile + SourceRowNumber` là duy nhất; đây không phải business key. |

EDA xác minh 14 dòng logical trùng trong toàn nguồn. Vì row ordinal và source order là một phần lineage, mọi dòng vẫn được load. Không có thao tác deduplicate tự động. Duplicate là một DQ warning/audit metric, không phải lý do xóa dữ liệu.

## 4. Null policy

- Staging preserve nguyên trạng NULL/blank đã parse thành SQL `NULL`; không tự điền chuỗi giả hoặc số giả.
- Nullable theo quan sát: `Gender`, `DrivAge`, `VehYear`, `VehModel`, `VehGroup`, `Area`, `State`, `StateAb`.
- Các measure exposure, premium, sum insured, claim count và claim amount là `NOT NULL` ở snapshot hiện tại.
- `State` và `StateAb` phải cùng có dữ liệu hoặc cùng NULL; mapping không-null phải nhất quán hai chiều.
- Khi DWH cần foreign key cho descriptor NULL, có thể dùng default/unknown dimension member có nhãn kỹ thuật rõ ràng. Member đó không tạo customer, policy hoặc business entity giả.

## 5. Invalid-value policy

| Nhóm rule | Phân loại | Xử lý |
|---|---|---|
| File thiếu, header không đọc được, schema khác | HARD CONTRACT FAILURE | Dừng batch trước staging. |
| Numeric parse failure, non-finite hoặc NULL ở measure bắt buộc | HARD CONTRACT FAILURE | Log DQ và dừng batch. |
| Exposure, premium, sum insured, claim count hoặc claim amount âm | HARD CONTRACT FAILURE | Log DQ và dừng batch. |
| `State`/`StateAb` chỉ có một bên hoặc mapping mâu thuẫn | HARD CONTRACT FAILURE | Log DQ và dừng batch. |
| Exposure/premium bằng 0 | VALID SOURCE VALUE | Giữ row; `ClaimFrequency`/`LossRatio` là NULL, không infinity. |
| `VehYear` NULL hoặc 0 | SUSPICIOUS / BUSINESS REVIEW | Giữ nguyên, không impute; report count. |
| 14 duplicate logical rows | AUDIT WARNING | Preserve source row, report count; không deduplicate. |
| `ExposFireRob` và `PremFireRob` đều bằng 0 trong snapshot | AUDIT-ONLY SOURCE CONSTANT | Giữ cột; không tự loại; thay đổi tương lai cần review trước khi nâng thành hard rule. |
| Claim count/amount pair không khớp | BUSINESS REVIEW WARNING | Các pair observed đều nhất quán; không suy diễn một threshold nghiệp vụ không có bằng chứng. |

## 6. Partition và batch semantics

1. Mỗi partition là một source batch bất biến có `SourceFile` riêng.
2. Ingest chỉ chấp nhận năm file đã freeze trong contract; không có wildcard ngầm định.
3. Batch success phải lưu source row count, staging row count, thời gian và trạng thái.
4. Rerun một partition đã `SUCCESS` phải trở thành no-op có ghi nhận hoặc trả về batch hiện có; không nạp trùng.
5. Một batch chỉ `SUCCESS` khi source row count bằng staging row count. Tổng staging phải bằng 1,965,355 sau năm batch.

## 7. Derived metrics và ML boundary

Metric dẫn xuất được định nghĩa tại `data-dictionary.md`. Claim count và claim amount là outcome của snapshot; chúng là `TARGET_DERIVED` để phân tích hiện tại và là `LEAKAGE` nếu dùng làm feature dự báo outcome cùng kỳ.

Các descriptor driver, vehicle và geography chỉ là `PRE_OUTCOME_FEATURE` nếu một use case tương lai chứng minh chúng có trước thời điểm prediction. Exposure, premium và sum insured là `REQUIRES_REVIEW` vì nguồn không cung cấp time semantics để loại trừ leakage. Không có model, metric model hoặc acceptance threshold nào được freeze trong contract này.

## 8. DQ baseline được yêu cầu downstream

Source/staging DQ phải kiểm tra schema, required columns, numeric parse/range, null policy, duplicate audit, categorical cardinality, State/StateAb mapping, denominator hữu hạn và source-to-staging reconciliation. Warehouse DQ phải kiểm tra FK, fact grain, technical lineage, dimension uniqueness và rerun consistency.
