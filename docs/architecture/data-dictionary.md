# Từ điển dữ liệu nguồn Track B — brvehins1

Trạng thái: `DONE` cho source data contract `P1-DATA-02`. Bằng chứng profile nằm tại `reports/data/brvehins1-profile.json`, `reports/data/brvehins1-column-profile.csv` và `reports/data/brvehins1-eda-summary.md`.

## Phạm vi

Contract này áp dụng duy nhất cho Track B: năm partition `data/raw/brvehins1/brvehins1[a-e].csv`, gồm 1,965,355 dòng và 23 cột. SUSEP là Track A độc lập; nó nằm ngoài dictionary và pipeline Track B này, không phải source thay thế hay join target.

Kiểu physical dưới đây là dtype quan sát qua pandas streaming. Kiểu SQL là mapping chuẩn để staging và DWH giữ được giá trị nguồn; chúng không làm phát sinh business identifier.

## Bổ sung precision từ raw lexical scan

Pandas `float64` không cho biết đầy đủ số chữ số thập phân trong text CSV. Khi nạp partition A ở `P1-INGEST-02`, một giá trị `ExposTotal` ở source row 35 có `0.00547945220023394`, nên `DECIMAL(19,6)` sẽ làm mất precision. Scanner streaming độc lập tại `reports/data/brvehins1-numeric-precision.json` đã đọc lại 1,965,355 dòng bằng `Decimal` và xác nhận:

- `ExposTotal` cần tối thiểu `DECIMAL(21,17)` (4 chữ số phần nguyên, 17 chữ số phần thập phân).
- `PremTotal` cần tối thiểu `DECIMAL(34,27)` (7 chữ số phần nguyên, 27 chữ số phần thập phân); ví dụ raw có `4.54747350886464e-13`.
- Các decimal measure còn lại không vượt precision của `DECIMAL(19,6)` trong snapshot này; các claim amount raw là số nguyên.

Đây là điều chỉnh contract dựa trên raw lexical evidence, không phải làm tròn hoặc cap source value.

## Nhóm DRIVER và VEHICLE

| Cột nguồn | Nhóm | Physical quan sát | SQL logical | Nullable | Ý nghĩa có bằng chứng | Validation / intended use |
|---|---|---|---|---|---|---|
| `Gender` | DRIVER | `str` | `NVARCHAR(20)` | Có | Nhãn category nguồn; có cả giá trị `Corporate`, nên không thể coi đơn giản là giới tính cá nhân. | Preserve NULL; cardinality 3 khi không null; dimension attribute; ML `PRE_OUTCOME_FEATURE` có điều kiện timing. |
| `DrivAge` | DRIVER | `str` | `NVARCHAR(20)` | Có | Nhóm tuổi dạng text, không phải tuổi số liên tục. | Preserve NULL; cardinality 5 khi không null; dimension attribute; ML `PRE_OUTCOME_FEATURE` có điều kiện timing. |
| `VehYear` | VEHICLE | `int64`/`float64` | `SMALLINT` | Có | Giá trị năm/mã năm xe theo nguồn; có 4 NULL và 8 giá trị 0. | Không âm khi có giá trị; `0` là `SUSPICIOUS`/business review, không bị thay đổi; dimension attribute; ML `PRE_OUTCOME_FEATURE` có điều kiện timing. |
| `VehModel` | VEHICLE | `str` | `NVARCHAR(255)` | Có | Nhãn model xe do nguồn cung cấp. | Preserve NULL; cardinality 4,259 khi không null; dimension attribute; ML `PRE_OUTCOME_FEATURE` có điều kiện timing. |
| `VehGroup` | VEHICLE | `str` | `NVARCHAR(255)` | Có | Nhãn nhóm xe do nguồn cung cấp. | Preserve NULL; cardinality 436 khi không null; dimension attribute; ML `PRE_OUTCOME_FEATURE` có điều kiện timing. |

## Nhóm GEOGRAPHY

| Cột nguồn | Nhóm | Physical quan sát | SQL logical | Nullable | Ý nghĩa có bằng chứng | Validation / intended use |
|---|---|---|---|---|---|---|
| `Area` | GEOGRAPHY | `str` | `NVARCHAR(100)` | Có | Nhãn khu vực do nguồn cung cấp. | Preserve NULL; cardinality 40 khi không null; geography dimension attribute; ML `PRE_OUTCOME_FEATURE` có điều kiện timing. |
| `State` | GEOGRAPHY | `str` | `NVARCHAR(100)` | Có | Tên bang/khu vực địa lý theo nguồn. | Preserve NULL; cardinality 27 khi không null; phải nhất quán với `StateAb` khi cả hai có giá trị. |
| `StateAb` | GEOGRAPHY | `str` | `CHAR(2)` | Có | Viết tắt bang/khu vực theo nguồn. | Preserve NULL; cardinality 27 khi không null; mapping hai chiều với `State` không có mâu thuẫn trong snapshot. |

## Nhóm EXPOSURE, PREMIUM và SUM_INSURED

| Cột nguồn | Nhóm | Physical quan sát | SQL logical | Nullable | Ý nghĩa có bằng chứng | Validation / intended use |
|---|---|---|---|---|---|---|
| `ExposTotal` | EXPOSURE | `float64` | `DECIMAL(21,17)` | Không | Measure exposure tổng theo nhãn nguồn. | Hữu hạn và không âm; lexical raw scale tối đa 17 được preserve; 51,762 giá trị 0 được giữ lại; `REQUIRES_REVIEW` cho ML vì timing chưa được chứng minh. |
| `ExposFireRob` | EXPOSURE | `int64` | `DECIMAL(19,6)` | Không | Measure exposure cho nhóm field fire/rob theo nhãn nguồn. | Hữu hạn và không âm; toàn bộ snapshot bằng 0, là source characteristic cần review chứ không bị xóa. |
| `PremTotal` | PREMIUM | `float64` | `DECIMAL(34,27)` | Không | Premium tổng theo nhãn nguồn. | Hữu hạn và không âm; lexical raw scale tối đa 27 được preserve; 51,762 giá trị 0 được giữ lại; `REQUIRES_REVIEW` cho ML vì có thể đồng thời với outcome. |
| `PremFireRob` | PREMIUM | `int64` | `DECIMAL(19,6)` | Không | Premium cho nhóm field fire/rob theo nhãn nguồn. | Hữu hạn và không âm; toàn bộ snapshot bằng 0, là source characteristic cần review. |
| `SumInsAvg` | SUM_INSURED | `float64` | `DECIMAL(19,6)` | Không | Giá trị insured average theo nhãn nguồn. | Hữu hạn và không âm; 140,667 giá trị 0 được giữ lại; `REQUIRES_REVIEW` cho ML vì timing chưa được chứng minh. |

## Nhóm CLAIM_COUNT và CLAIM_AMOUNT

| Cột nguồn | Nhóm | Physical quan sát | SQL logical | Nullable | Ý nghĩa có bằng chứng | Validation / intended use |
|---|---|---|---|---|---|---|
| `ClaimNbRob` | CLAIM_COUNT | `int64` | `INT` | Không | Số claim cho category `Rob` theo nhãn nguồn. | Integer, không âm; fact measure; `TARGET_DERIVED` và `LEAKAGE` cho dự báo outcome cùng kỳ. |
| `ClaimNbPartColl` | CLAIM_COUNT | `int64` | `INT` | Không | Số claim cho category `PartColl` theo nhãn nguồn. | Integer, không âm; fact measure; `TARGET_DERIVED` và `LEAKAGE` cho dự báo outcome cùng kỳ. |
| `ClaimNbTotColl` | CLAIM_COUNT | `int64` | `INT` | Không | Số claim cho category `TotColl` theo nhãn nguồn. | Integer, không âm; fact measure; `TARGET_DERIVED` và `LEAKAGE` cho dự báo outcome cùng kỳ. |
| `ClaimNbFire` | CLAIM_COUNT | `int64` | `INT` | Không | Số claim cho category `Fire` theo nhãn nguồn. | Integer, không âm; fact measure; `TARGET_DERIVED` và `LEAKAGE` cho dự báo outcome cùng kỳ. |
| `ClaimNbOther` | CLAIM_COUNT | `int64` | `INT` | Không | Số claim cho category `Other` theo nhãn nguồn. | Integer, không âm; fact measure; `TARGET_DERIVED` và `LEAKAGE` cho dự báo outcome cùng kỳ. |
| `ClaimAmountRob` | CLAIM_AMOUNT | `int64`/`float64` | `DECIMAL(19,6)` | Không | Claim amount cho category `Rob` theo nhãn nguồn. | Hữu hạn, không âm; fact measure; `TARGET_DERIVED` và `LEAKAGE` cho dự báo outcome cùng kỳ. |
| `ClaimAmountPartColl` | CLAIM_AMOUNT | `int64` | `DECIMAL(19,6)` | Không | Claim amount cho category `PartColl` theo nhãn nguồn. | Hữu hạn, không âm; fact measure; `TARGET_DERIVED` và `LEAKAGE` cho dự báo outcome cùng kỳ. |
| `ClaimAmountTotColl` | CLAIM_AMOUNT | `int64`/`float64` | `DECIMAL(19,6)` | Không | Claim amount cho category `TotColl` theo nhãn nguồn. | Hữu hạn, không âm; fact measure; `TARGET_DERIVED` và `LEAKAGE` cho dự báo outcome cùng kỳ. |
| `ClaimAmountFire` | CLAIM_AMOUNT | `int64` | `DECIMAL(19,6)` | Không | Claim amount cho category `Fire` theo nhãn nguồn. | Hữu hạn, không âm; fact measure; `TARGET_DERIVED` và `LEAKAGE` cho dự báo outcome cùng kỳ. |
| `ClaimAmountOther` | CLAIM_AMOUNT | `int64` | `DECIMAL(19,6)` | Không | Claim amount cho category `Other` theo nhãn nguồn. | Hữu hạn, không âm; fact measure; `TARGET_DERIVED` và `LEAKAGE` cho dự báo outcome cùng kỳ. |

Các khái niệm `Rob`, `PartColl`, `TotColl`, `Fire` và `Other` được giữ nguyên theo tên field nguồn. Không mở rộng ý nghĩa nghiệp vụ vượt quá bằng chứng hiện có.

## Metric dẫn xuất đã xác minh

| Metric | Công thức | Chính sách mẫu số / null | Phân loại |
|---|---|---|---|
| `TotalClaimCount` | `ClaimNbRob + ClaimNbPartColl + ClaimNbTotColl + ClaimNbFire + ClaimNbOther` | NULL nếu bất kỳ input count bắt buộc nào NULL; snapshot hiện tại không có NULL. | `TARGET_DERIVED` |
| `TotalClaimAmount` | Tổng năm cột `ClaimAmount*` | NULL nếu bất kỳ input amount bắt buộc nào NULL; snapshot hiện tại không có NULL. | `TARGET_DERIVED` |
| `HasClaim` | `CASE WHEN TotalClaimCount > 0 THEN 1 ELSE 0 END` | NULL nếu `TotalClaimCount` NULL. | `TARGET_DERIVED` |
| `ClaimFrequency` | `TotalClaimCount / ExposTotal` | NULL khi `ExposTotal <= 0`; không tạo infinity. | `TARGET_DERIVED` |
| `LossRatio` | `TotalClaimAmount / PremTotal` | NULL khi `PremTotal <= 0`; không cap outlier. | `TARGET_DERIVED` |

Xem chính sách đầy đủ, grain, technical identity và batch semantics tại [source-data-contract.md](source-data-contract.md).
