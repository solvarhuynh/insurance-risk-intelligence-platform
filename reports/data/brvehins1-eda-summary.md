# EDA và Source Profile — brvehins1

> Bổ sung 2026-09-22: `float64` không phản ánh đủ lexical precision của raw CSV. Xem `brvehins1-numeric-precision.json`: `ExposTotal` cần `DECIMAL(21,17)` và `PremTotal` cần `DECIMAL(34,27)` để không làm tròn source value. Các bảng thống kê dưới đây vẫn là profile giá trị số, không phải quyết định precision SQL.

Kết quả được tạo bằng streaming chunk; raw không bị sửa đổi.

## Partition và schema

| File | Bytes | Số dòng | Dòng trùng logic gặp trong lúc quét |
|---|---:|---:|---:|
| `brvehins1a.csv` | 60,499,054 | 393,071 | 0 |
| `brvehins1b.csv` | 60,497,433 | 393,071 | 4 |
| `brvehins1c.csv` | 60,481,086 | 393,071 | 2 |
| `brvehins1d.csv` | 60,491,192 | 393,071 | 2 |
| `brvehins1e.csv` | 60,501,172 | 393,071 | 6 |

Tổng số dòng: **1,965,355**. Số cột: **23**. Schema tương thích: **True**.

## Missing và duplicate

| Cột | Missing | Missing % |
|---|---:|---:|
| `Gender` | 88,189 | 4.487179% |
| `DrivAge` | 284,948 | 14.498551% |
| `VehYear` | 4 | 0.000204% |
| `VehModel` | 120,515 | 6.131971% |
| `VehGroup` | 120,515 | 6.131971% |
| `Area` | 13 | 0.000661% |
| `State` | 13 | 0.000661% |
| `StateAb` | 13 | 0.000661% |
| `ExposTotal` | 0 | 0.000000% |
| `ExposFireRob` | 0 | 0.000000% |
| `PremTotal` | 0 | 0.000000% |
| `PremFireRob` | 0 | 0.000000% |
| `SumInsAvg` | 0 | 0.000000% |
| `ClaimNbRob` | 0 | 0.000000% |
| `ClaimNbPartColl` | 0 | 0.000000% |
| `ClaimNbTotColl` | 0 | 0.000000% |
| `ClaimNbFire` | 0 | 0.000000% |
| `ClaimNbOther` | 0 | 0.000000% |
| `ClaimAmountRob` | 0 | 0.000000% |
| `ClaimAmountPartColl` | 0 | 0.000000% |
| `ClaimAmountTotColl` | 0 | 0.000000% |
| `ClaimAmountFire` | 0 | 0.000000% |
| `ClaimAmountOther` | 0 | 0.000000% |

Exact duplicate rows toàn nguồn: **14**; distinct logical rows: **1,965,341**.

## Numeric ranges và quantiles

| Cột | Min | P50 | P95 | P99 | Max | Âm | Bằng 0 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `VehYear` | 0.000000 | 2,007.000000 | 2,011.000000 | 2,011.000000 | 2,012.000000 | 0 | 8 |
| `ExposTotal` | 0.000000 | 0.530000 | 11.790000 | 44.270000 | 8,078.440000 | 0 | 51,762 |
| `ExposFireRob` | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 1,965,355 |
| `PremTotal` | 0.000000 | 887.820000 | 13,667.551000 | 48,589.017400 | 6,478,755.130000 | 0 | 51,762 |
| `PremFireRob` | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 1,965,355 |
| `SumInsAvg` | 0.000000 | 29,810.530000 | 107,289.305000 | 197,153.479000 | 1,307,269.940000 | 0 | 140,667 |
| `ClaimNbRob` | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 164.000000 | 0 | 1,923,094 |
| `ClaimNbPartColl` | 0.000000 | 0.000000 | 1.000000 | 4.000000 | 1,617.000000 | 0 | 1,749,216 |
| `ClaimNbTotColl` | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 66.000000 | 0 | 1,932,654 |
| `ClaimNbFire` | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 6.000000 | 0 | 1,963,815 |
| `ClaimNbOther` | 0.000000 | 0.000000 | 2.000000 | 8.000000 | 1,278.000000 | 0 | 1,775,601 |
| `ClaimAmountRob` | 0.000000 | 0.000000 | 0.000000 | 26,685.000000 | 4,421,765.000000 | 0 | 1,923,094 |
| `ClaimAmountPartColl` | 0.000000 | 0.000000 | 4,148.000000 | 17,244.000000 | 2,289,213.000000 | 0 | 1,749,216 |
| `ClaimAmountTotColl` | 0.000000 | 0.000000 | 0.000000 | 25,024.000000 | 2,201,873.000000 | 0 | 1,932,654 |
| `ClaimAmountFire` | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 581,152.000000 | 0 | 1,963,815 |
| `ClaimAmountOther` | 0.000000 | 0.000000 | 217.000000 | 1,664.000000 | 967,914.000000 | 0 | 1,775,601 |
| `TotalClaimCount` | 0.000000 | 0.000000 | 3.000000 | 12.000000 | 1,637.000000 | 0 | 1,602,279 |
| `TotalClaimAmount` | 0.000000 | 0.000000 | 9,347.000000 | 53,278.000000 | 8,273,940.000000 | 0 | 1,602,279 |
| `ClaimFrequency` | 0.000000 | 0.000000 | 0.881057 | 4.000000 | 13,504.999642 | 0 | 1,602,279 |
| `LossRatio` | 0.000000 | 0.000000 | 1.339572 | 14.891820 | 87,960,930,222,080.015625 | 0 | 1,602,279 |

## Derived metric distribution

HasClaim: có claim `363,076`, không claim `1,602,279`, thiếu `0`.

## Kiểm tra chéo

- `rows_with_state`: 1,965,342
- `rows_with_state_ab`: 1,965,342
- `rows_with_state_pair`: 1,965,342
- `zero_or_negative_exposure`: 51,762
- `zero_or_negative_premium`: 51,762
- `amount_positive_count_zero`: 0
- `count_positive_amount_zero`: 0
- `fire_rob_exposure_exceeds_total`: 0
- `fire_rob_premium_exceeds_total`: 0

## Đánh giá grain

Mỗi dòng là một quan sát tổng hợp về exposure, premium và claim cho một tổ hợp thuộc tính người lái, xe và địa lý; nguồn không cung cấp mã business identifier rõ ràng.

- Natural PolicyID: Không quan sát thấy trong 23 cột nguồn.
- Natural CustomerID: Không quan sát thấy trong 23 cột nguồn.
- Technical identity: SourceFile + SourceRowNumber; SourceRecordHash chỉ là fingerprint nội dung.

Mâu thuẫn State -> StateAb: 0. Mâu thuẫn StateAb -> State: 0.

Thời gian chạy profile: 330.018 giây.
