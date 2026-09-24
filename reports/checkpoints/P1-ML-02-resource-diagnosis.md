# P1-ML-02 — Chẩn đoán resource trước khi huấn luyện lại

Kết luận: `PASS`  
Ngày: 2026-09-23

## Lần trước nghẽn ở đâu?

Lần thử cũ extract toàn bộ `1,965,355` rows cùng bảy categorical feature vào
pandas, sau đó chạy `StratifiedGroupKFold` trên gần `1,965,323` hash group và
fit preprocessing/model. Process đạt khoảng **0.92 GB working set** trước khi
host dừng nó. Không có artifact được tạo từ lần thử đó.

Đây không phải do RandomForest, GridSearchCV hoặc training song song: code cũ
dùng `LogisticRegression(saga, n_jobs=-1)`, giữ full frame, tạo nhiều copy
split/DataFrame và dự kiến lặp OHE cho nhiều model. `n_jobs=-1` cũng không phù
hợp với local memory budget.

## Evidence có thể đo

| Item | Giá trị |
|---|---:|
| Toàn bộ fact | 1,965,355 rows |
| Distinct source hash | 1,965,323 |
| Duplicate-hash excess | 32 |
| Cardinality `VehModel` | 4,259 |
| Cardinality `VehGroup` | 436 |
| Các cardinality khác | Gender 3, DrivAge 5, VehYear 73, Area 40, StateAb 27 |
| Working set của lần bounded 300k | khoảng 0.92 GB trước khi dừng |

`VehModel` tạo hàng nghìn one-hot columns. One-hot vẫn đúng về semantics,
nhưng full source frame chứa object/string columns, group splitting và nhiều
copy làm peak memory lớn. Matrix OHE bản thân có thể sparse; vấn đề là toàn bộ
feature frame và các intermediate object cùng tồn tại.

## Lần này đổi gì?

```text
Không đổi: target, approved feature, leakage policy, SourceRecordHash grouping
Đổi:  full DWH frame → deterministic bounded DWH population 100,004 rows
      dense/default copies → sparse float32 OHE
      saga + n_jobs=-1 → single-process SGD logistic-loss / ComplementNB
      một lần lớn → progressive 4k → 24k → 60k training rows
```

Population có 18,474 positive và 81,526 negative hash groups; prevalence được
giữ gần source. Group vẫn complete, `StratifiedGroupKFold` vẫn giữ hash không
qua train/validation/test. Đây là giới hạn resource được ghi rõ, không phải
thay canonical dataset hoặc thay bài toán ML.

## Điều không làm

- Không dùng raw CSV hoặc source legacy.
- Không đưa claim count/amount/ratio vào feature.
- Không dùng dense one-hot, GridSearchCV, full-data cross-validation hay model zoo.
- Không gọi result là future customer/policy prediction.

## Kết luận

`PASS`: bottleneck đã có evidence và strategy mới giải quyết memory/runtime mà
không làm yếu data contract.
