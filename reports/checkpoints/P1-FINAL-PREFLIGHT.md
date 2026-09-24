# P1-FINAL-PREFLIGHT — Có thể bắt đầu Track A mà không làm hỏng Track B không?

## Stage này giải quyết vấn đề gì?

Preflight xác nhận kiến trúc đa track đã đúng và Track B vẫn hoạt động trước khi tạo bất kỳ object SUSEP nào. Nó giống kiểm tra máy đang chạy trước khi lắp thêm một dây chuyền mới: nếu máy cũ đã lỗi thì không được tiếp tục.

## Trước stage này project thiếu gì?

Có source strategy và historical runtime evidence, nhưng thiếu một lần smoke check tập trung trước finalization. Đặc biệt phải tách rõ SUSEP Track A với brvehins1 Track B, thay vì xem database chung là bằng chứng hai source đã join.

## Agent đã kiểm tra những gì?

| Kiểm tra | Kết quả | Evidence |
|---|---|---|
| Kiến trúc current | PASS | README, project-scope, source-strategy và validator mô tả SUSEP Track A, brvehins1 Track B, không fake join |
| SQL Server / DWH_Insurance | PASS | Container insurance_sqlserver Up; sqlcmd chạy production DQ |
| Track-B staging / fact | PASS | stg.BrVehIns1 = 1,965,355; dwh.FactRiskObservation = 1,965,355 |
| Track-B production DQ | PASS | 15 rules, mọi hard rule PASS trong run label p1-final-preflight |
| ML artifact | PASS trong declared .venv | claim_risk_model_v001.joblib load thành Pipeline, có predict_proba; metadata tồn tại |
| Prediction store | PASS | bounded_held_out_test = 20,000 rows; duplicate technical identity = 0 |
| Idempotency contract | PASS | Unique identity SourceFile + SourceRowNumber + ScoringPopulation + ModelVersion vẫn tồn tại ở V10 và SQL query không thấy duplicate |

## Runtime evidence là gì?

Production Track-B DQ đã chạy trực tiếp trên SQL Server. Query reconciliation trả về:

~~~text
StagingRows:       1,965,355
FactRows:          1,965,355
PredictionRows:       20,000
Duplicate identities:       0
~~~

Artifact được tạo bởi scikit-learn 1.7.2. Host global Python hiện có scikit-learn 1.9.0 nên load artifact lỗi compatibility; declared .venv có scikit-learn 1.7.2 và joblib 1.5.2, load PASS. Đây là dependency-boundary requirement, không phải model regression.

## Owner cần hiểu khái niệm gì?

**Smoke check** là kiểm tra ngắn nhưng thật trên các đường quan trọng, như bật máy và thử phanh trước khi đi đường dài. **Idempotency** nghĩa rerun cùng semantics không nhân row: Track B bảo đảm bằng unique key prediction. Hai khái niệm này bảo vệ thành quả cũ khi thêm Track A.

## Owner chưa cần học gì?

Chưa cần học DDL SUSEP, query plan hay Airflow trong stage này. Mục tiêu chỉ là xác nhận nền cũ an toàn.

## Tôi tự kiểm tra thế nào?

1. Chạy docker compose ps.
2. Chạy SQL Track-B DQ entry point.
3. Query count staging/fact/prediction theo contract.
4. Dùng .venv Scripts python, không dùng Python global khác version, để load artifact.

## Điều gì có thể nhìn đúng nhưng thực ra sai?

Artifact file tồn tại không đủ: version scikit-learn không khớp vẫn làm load fail. Docker container Up cũng không đủ: phải chạy DQ/reconciliation query. Và hai tracks cùng trong DWH_Insurance không tạo relationship row-level.

## Stage verdict

**PASS.** Có thể bắt đầu P1-SUSEP-01. Raw Track B không bị reload, EDA đầy đủ hay model retraining không được chạy.

