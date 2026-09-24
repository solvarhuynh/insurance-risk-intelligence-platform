# ML đang giải bài toán gì?

P1-ML-02 đến P1-ML-05 đạt `RUNTIME_PASS`. Model ước lượng association cross-sectional với `HasClaim` quan sát được trên aggregate risk observation; nó không dự đoán future customer/policy claim, pricing, causality hoặc production forecast.

```text
HasClaim = 1 khi TotalClaimCount > 0
HasClaim = 0 khi TotalClaimCount = 0
```

# Feature đi vào model từ đâu?

```text
brvehins1 CSV → staging → dimensions + FactRiskObservation → bounded ML extraction → preprocessing + model → SQL prediction
```

Feature estimator là `Gender`, `DrivAge`, `VehYear`, `VehModel`, `VehGroup`, `Area`, `StateAb`. `SourceFile + SourceRowNumber` giữ lineage nhưng không đi vào model.

# Vì sao một số cột bị cấm dùng?

**Data Leakage** — rò rỉ đáp án vào input, như nhìn đáp án trước khi làm bài. Nếu target là `HasClaim`, `ClaimNb*`, `ClaimAmount*`, `TotalClaimCount`, `TotalClaimAmount`, `HasClaim`, `ClaimFrequency`, `LossRatio` là outcome cùng snapshot và bị cấm. Premium/exposure/sum-insured cũng bị loại vì source chưa chứng minh chúng có mặt tại prediction time.

# Train, validation và test khác nhau để làm gì?

Train là sách luyện, validation là bài kiểm tra thử để chọn model, test là đề thi niêm phong cuối cùng. Không có event time nên không bịa chronological split. `StratifiedGroupKFold(5, seed=20260923)` group theo `SourceRecordHash` để logical duplicate không đi qua split khác.

| Split | Rows | Positive rows | Positive rate |
|---|---:|---:|---:|
| Train | 60,002 | 11,025 | 18.374% |
| Validation | 20,002 | 3,680 | 18.398% |
| Held-out test | 20,000 | 3,769 | 18.845% |

# Tại sao lần trước training bị nghẽn?

Lần cũ materialize full `1,965,355` DWH rows, giữ pandas/split copies và one-hot preprocessing cho nhiều model. `VehModel` có 4,259 category, `VehGroup` có 436; process đạt khoảng **0.92 GB working set** trước khi host dừng. `saga` với `n_jobs=-1` không hợp local resource budget; không có artifact từ lần thử đó.

# Lần này resource problem được giải như thế nào?

- DWH chọn deterministic 18,474 positive + 81,526 negative hash group, thành 100,004 rows; source canonical không bị thay.
- **One-Hot Encoding** biến category thành cột 0/1; dùng sparse `float32`.
- **Sparse Matrix** chỉ lưu ô khác 0; phù hợp vì mỗi row chỉ có 7 non-zero trên hàng nghìn cột.
- Train tăng dần 4,000 → 23,999 → 60,000 rows.
- Dùng single-process `SGDClassifier(loss="log_loss")` và `ComplementNB`; không dense matrix, full-data CV, GridSearchCV, model zoo hay worker không giới hạn.

| Train rows | Sparse columns | Train time | Validation ROC-AUC | PR-AUC |
|---:|---:|---:|---:|---:|
| 4,000 | 1,706 | 0.210 s | 0.75695 | 0.41794 |
| 23,999 | 2,935 | 0.683 s | 0.79440 | 0.48472 |
| 60,000 | 3,528 | 1.552 s | 0.80208 | 0.49994 |

# Baseline cho biết điều gì?

**Class Imbalance** là mất cân bằng lớp: chỉ khoảng 18.4% row positive. **Baseline** dummy luôn đoán no-claim có accuracy 81.60%, nhưng ROC-AUC 0.5, PR-AUC 0.18398 và precision/recall/F1 bằng 0. Accuracy riêng lẻ gây hiểu lầm.

SGD logistic-loss baseline validation: ROC-AUC 0.80208, PR-AUC 0.49994, precision 0.68178, recall 0.20027, F1 0.30960 tại threshold 0.5.

# Các model được so sánh ra sao?

| Model | PR-AUC | ROC-AUC | Train time | Inference | Nhận xét |
|---|---:|---:|---:|---:|---|
| Majority dummy | 0.18398 | 0.50000 | 1.219 s | 0.195 s | mốc tham chiếu |
| SGD logistic-loss | **0.49994** | **0.80208** | 1.440 s | 0.197 s | ranking tốt nhất |
| ComplementNB | 0.40561 | 0.76972 | **1.059 s** | 0.205 s | nhanh nhưng ranking yếu hơn |

`LogisticRegression(saga, n_jobs=-1)` là `RESOURCE_REJECTED` vì full-DWH thử trước vượt local budget. Không broad hyperparameter tuning.

# Tại sao final model được chọn?

`SGDClassifier(loss="log_loss")` dẫn đầu validation PR-AUC và ROC-AUC, inference nhanh, sparse-compatible, single-process, ít dependency và linear nên dễ vận hành. Selection ưu tiên PR-AUC trước vì target imbalanced; không chỉ chọn decimal ROC-AUC lớn nhất.

**ROC-AUC** đo khả năng xếp positive cao hơn negative ở nhiều threshold. **PR-AUC/Average Precision** tập trung chất lượng positive ranking trong data imbalanced. **Precision** là trong row model gắn positive, bao nhiêu row thật positive. **Recall** là trong positive thật, model tìm được bao nhiêu. **F1** cân bằng precision/recall. **Confusion Matrix** là bảng đếm dự đoán đúng/sai.

| Held-out test metric | Kết quả |
|---|---:|
| ROC-AUC | 0.808815 |
| PR-AUC | 0.513523 |
| Precision @ 0.5 | 0.699358 |
| Recall @ 0.5 | 0.202441 |
| F1 @ 0.5 | 0.313992 |
| Confusion matrix | `[[15903,328],[3006,763]]` |

**Threshold** là vạch probability đổi score thành label. 0.5 chỉ là default để report nhất quán, không phải production decision threshold đã tối ưu.

# Model artifact thực sự là gì?

Artifact là file chứa preprocessing và estimator đã fit, không chỉ là coefficient. File local là `ml/artifacts/claim_risk_model_v001.joblib` và `ml/artifacts/claim_risk_model_v001.metadata.json`. Metadata chứa version, target, framing, feature, leakage exclusion, split, metrics, dependency, Git state, resource strategy và limitation.

Fresh Python process đã load artifact, score 100 deterministic test rows, có đủ 100 probability không missing, range `0.0000750320`–`0.7419331670`, và probability trùng với pipeline trong process train.

# Batch scoring hoạt động thế nào?

**Inference** là model nhận feature để tạo probability, không học lại. **Batch Scoring** là inference cho một lô. Lô hiện hành là `bounded_held_out_test` 20,000 rows, nên honest name là out-of-sample batch inference demonstration.

```text
bounded held-out DWH test + claim_risk_model_v001.joblib
                         ↓ predict_proba
                  #PredictionLoad temporary table
                         ↓ MERGE
             dwh.RiskObservationPrediction
```

# Prediction được lưu ở đâu?

`dwh.RiskObservationPrediction` có grain source technical identity + model version + scoring population. Nó lưu `SourceFile`, `SourceRowNumber`, `SourceRecordHash`, `ModelVersion`, `ScoreProbability`, `ThresholdValue`, `PredictedHasClaim`, `ScoringRunId`, `ScoredAtUtc`. Không có customer fact vì source không chứng minh customer.

# Làm sao biết scoring không mất hoặc nhân đôi rows?

Lần đầu: expected 20,000 = predicted 20,000 = SQL rows 20,000; difference 0, duplicate source identity 0. Rerun cùng model/population: vẫn 20,000 SQL rows, difference 0, duplicate 0.

**Idempotency** là chạy lại không nhân đôi. Unique key `SourceFile + SourceRowNumber + ScoringPopulation + ModelVersion`; SQL MERGE cập nhật row cũ bằng `ScoringRunId` mới. Evidence nằm tại `reports/data/p1-ml-batch-scoring.json`.

# Tôi nên đọc file nào?

1. `docs/ml/ml-data-contract.md`.
2. `reports/checkpoints/P1-ML-02-resource-diagnosis.md`.
3. `ml/modeling.py`.
4. `ml/train_risk_model.py`.
5. `reports/data/p1-ml-resource-scaling.json` và `p1-ml-model-comparison.json`.
6. `reports/checkpoints/P1-ML-02.md` đến `P1-ML-05.md`.
7. `ml/predict_risk_batch.py` và V10 migration.

# Tôi có thể tự kiểm tra ML như thế nào?

1. Set `SQLSERVER_SA_PASSWORD`; chạy `python ml/train_risk_model.py`.
2. Mở metadata artifact để xem feature/limitation.
3. Chạy `python ml/predict_risk_batch.py`; xem JSON reconciliation.
4. Chạy lại scorer; SQL count không tăng quá 20,000.
5. Query `dwh.RiskObservationPrediction` theo model/population.
6. Chạy `EXEC dq.sp_RunQualityGate @RunLabel=N'manual-ml-check';`.
7. So sánh `reports/data/p1-ml-*.json` với checkpoint.

# Tôi chưa cần học gì?

Chưa cần deep mathematics của gradient descent, advanced tuning, Airflow internals, performance tuning hay Power BI. Trước hết cần hiểu grain, target, leakage, split, sparse preprocessing, metric, artifact và scoring reconciliation.

# Tôi đã cần hiểu những thuật ngữ nào?

| English term | Nghĩa đơn giản | Ví dụ đời thường | Ví dụ repository và vì sao quan trọng |
|---|---|---|---|
| **Feature** | thông tin đưa cho model | manh mối trước khi trả lời | `VehModel`, `Area`; chỉ field biết được theo contract mới được dùng |
| **Target** | đáp án model học | đáp án trong bài luyện | `HasClaim`; quyết định model đang học điều gì |
| **Data Leakage** | input chứa đáp án | xem đáp án trước thi | `ClaimAmount*` bị cấm để metric không giả tạo |
| **Class Imbalance** | một lớp hiếm hơn lớp kia | hộp 82 bi trắng, 18 bi đỏ | positive rate khoảng 18.4%; không dùng accuracy một mình |
| **Train Set** | dữ liệu model được phép học | sách bài tập | 60,002 rows trước final cap; fit preprocessing/estimator |
| **Validation Set** | dữ liệu để chọn model | thi thử | 20,002 rows; chọn SGD thay ComplementNB |
| **Test Set** | dữ liệu chỉ mở ở cuối | đề thi niêm phong | 20,000 held-out rows; báo cáo final metric |
| **Stratification** | giữ tỷ lệ lớp gần nhau | chia đều màu bi vào mỗi hộp | group folds giữ HasClaim prevalence giữa split |
| **Preprocessing** | chuẩn bị input trước model | rửa và cắt rau trước nấu | imputer/OHE nằm trong Pipeline và chỉ fit train |
| **One-Hot Encoding** | category thành cột 0/1 | checklist chọn một ô | `VehModel` thành feature columns để linear model hiểu |
| **Sparse Matrix** | chỉ lưu ô khác 0 | chỉ ghi ghế có người ngồi | OHE 60k × 3,528 có density 0.1984%, giảm memory |
| **Baseline** | mốc tối thiểu để so | cân với một thước đo chuẩn | majority dummy cho thấy accuracy 81.6% không đủ |
| **ROC-AUC** | chất lượng xếp positive cao hơn negative | xếp người cần ưu tiên lên trước | final test 0.808815, đo ranking nhiều threshold |
| **PR-AUC** | chất lượng tìm positive hiếm | lọc đúng thư quan trọng trong nhiều thư thường | final test 0.513523; metric ưu tiên selection |
| **Precision** | dự đoán positive có bao nhiêu đúng | gọi 10 người cần hỗ trợ, bao nhiêu người thật cần | test 0.699358 ở 0.5 |
| **Recall** | tìm được bao nhiêu positive thật | trong mọi người cần hỗ trợ, đã gọi được bao nhiêu | test 0.202441; thấy tradeoff threshold |
| **F1** | cân bằng precision và recall | điểm dung hòa hai kỹ năng | test 0.313992; không thay thế PR-AUC |
| **Confusion Matrix** | bảng đếm dự đoán đúng/sai | bảng kết quả đúng/sai | `[[15903,328],[3006,763]]`, làm lỗi cụ thể nhìn thấy được |
| **Threshold** | vạch đổi probability thành label | mốc điểm đỗ | 0.5 là default report, chưa phải business policy |
| **Model Artifact** | gói model đã sẵn sàng load | hộp dụng cụ đã đóng gói | `.joblib` gồm preprocessing + estimator để process mới score |
| **Inference** | dùng model đã học để ra score | làm bài bằng kiến thức đã học, không học lại | `predict_proba` trên held-out DWH test |
| **Batch Scoring** | inference cho cả lô | chấm cả tập bài | 20,000 test rows vào SQL Server |

Các thuật ngữ này quan trọng hơn deep mathematics ở milestone hiện tại: chúng
quyết định kết quả ML có trung thực, reload được và trace được hay không.

# 15 câu tự kiểm tra

1. Một row model đại diện cho gì?
2. Model không dự đoán điều gì?
3. Target formula là gì?
4. Vì sao `ClaimAmount*` là leakage?
5. Vì sao không chronological split?
6. Group key là gì?
7. Vì sao dùng sparse OHE?
8. Vì sao không full DWH training?
9. Dummy accuracy cao có nghĩa model tốt không?
10. Final model là gì?
11. Held-out test PR-AUC là bao nhiêu?
12. Artifact ở đâu?
13. Scoring population là gì?
14. Prediction table grain là gì?
15. Rerun scorer chống duplicate thế nào?

# Đáp án

1. Aggregate risk observation. 2. Future customer/policy claim. 3. Total claim count lớn hơn 0. 4. Nó là outcome đã biết. 5. Source không có event time. 6. `SourceRecordHash`. 7. Mỗi row có ít non-zero trên hàng nghìn cột. 8. Lần cũ chạm khoảng 0.92 GB local working set. 9. Không; imbalance tạo accuracy giả. 10. SGD logistic-loss. 11. 0.513523. 12. `ml/artifacts/claim_risk_model_v001.joblib`. 13. Bounded held-out test 20,000 rows. 14. Technical source identity + model + population. 15. Unique key và SQL MERGE update row cũ.

# Kết luận

ML milestone đã PASS trong ranh giới resource rõ ràng. Bước tiếp theo được khuyến nghị là `P1-ORCH-01 / P1-ORCH-02`, chỉ để điều phối các bước ML/DQ đã chạy tay thành công. Report này không triển khai Airflow.
