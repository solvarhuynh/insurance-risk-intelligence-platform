# Tôi đang học Insurance Data Platform như thế nào?

## Bức tranh lớn

Repository là một platform dữ liệu bảo hiểm nhiều track. Hãy hình dung khu công nghiệp: các xưởng dùng chung điện, bảo vệ và bảng điều khiển, nhưng mỗi xưởng dùng nguyên liệu khác nhau và không trộn hóa đơn của nhau.

- **Track A — SUSEP:** Market Data Warehouse, data quality và performance tuning.
- **Track B — brvehins1:** Motor risk Data Warehouse, risk analytics và bounded ML.
- **Track C — Prudential:** mục tiêu underwriting ban đầu, chưa có source vật lý.

`ACTIVE_CANONICAL` chỉ có nghĩa “nguồn chuẩn trong track đó”. SUSEP và brvehins1 đều active canonical; không dataset nào là chủ của toàn repo.

## Grain quyết định thiết kế

**Grain** là câu trả lời cho “một row là gì?”. Nó giống đơn vị ghi trên hóa đơn: không biết hóa đơn tính theo sản phẩm, ngày hay cửa hàng thì không thể cộng/join đáng tin.

| Track | Grain đã xác minh | Không được tự bịa |
|---|---|---|
| SUSEP | `company_code + year_month + product + state` market observation | customer, policy, claim event, exposure |
| brvehins1 | aggregate motor-risk observation; identity `SourceFile + SourceRowNumber` | customer, policy, future claim event |

Vì không có business key chung, không join SUSEP với brvehins1/Prudential. Cùng nói về insurance không đủ bằng chứng để nối từng dòng.

## Track A đã chạy như thế nào?

```text
insurance_dataset.csv (raw immutable)
  → streaming loader + source fingerprint
  → stg.SusepInsuranceMarket
  → DimSusepMonth / Company / Product / State
  → FactSusepInsuranceMarket
  → source → staging → fact reconciliation
  → SUSEP DQ → performance / Market BI subject area
```

Runtime evidence: 8.338.214 source = staging = fact rows. Premium/claims cũng bằng nhau qua ba lớp. Rerun cùng fingerprint trả `SKIPPED`; nó không duplicate 8,3 triệu records.

## Track B đã chạy như thế nào?

```text
five brvehins1 partitions
  → stg.BrVehIns1
  → DimDriverProfile / DimVehicle / DimGeography
  → FactRiskObservation → Track-B DQ
  → bounded ML artifact → RiskObservationPrediction
```

Runtime evidence: staging = fact = 1.965.355; 20.000 prediction held-out không duplicate identity. Artifact phải được load bằng dependency pin scikit-learn 1.7.2.

## DQ, incremental và ML cần hiểu ở mức nào?

**DQ gate** là trạm kiểm soát: hard failure chặn downstream; warning chỉ ghi nhận điều cần review. Ví dụ premium âm SUSEP có thể là accounting adjustment, nên current contract là warning chứ không lén xóa dữ liệu.

**Idempotency** là chạy lại không nhân bản kết quả. SUSEP dùng source fingerprint/batch audit; Track B dùng contract identity cho staging/prediction. **Synthetic CDC** Track B là kỹ thuật minh họa có kiểm soát, không phải tuyên bố file CSV có stream thay đổi thật.

ML Track B học association với `HasClaim` đã quan sát trên aggregate observation. Nó không dự đoán claim tương lai của customer/policy. Claim counts/amounts bị loại khỏi feature để tránh leakage, như không được nhìn đáp án trước khi thi.

## Airflow đã điều phối điều gì?

Airflow DAG `insurance_data_platform` đã có valid run 12/12 task success. Nó chạy hai nhánh độc lập:

```text
Track A: ingest → DWH → reconciliation → DQ → market consumer ready
Track B: precheck → incremental audit → DQ → score → prediction reconciliation → risk consumer ready
```

Controlled Track-A DQ failure làm Track-A consumer `upstream_failed` trong khi Track-B consumer `success`. DAG arrows biểu thị thứ tự task, không là database join.

## Performance và BI đang ở đâu?

Track A Q1 giảm reads 317.528 → 3.364; Q2 giảm 317.528 → 3.734 sau hai covering index có căn cứ. Đọc `reports/performance-report.md` để hiểu storage/write trade-off.

Power BI semantic model đã thiết kế hai subject area tách biệt. Chưa có Power BI Desktop/PBIP toolchain trong runtime để tạo/refresh artifact thật; đây là `BLOCKED_MANUAL`, không được thay bằng `.pbix` giả.

## Nên đọc gì tiếp?

1. `FINAL_PROJECT_GUIDE.md` để học toàn bộ flow và 30 câu tự kiểm tra.
2. `docs/architecture/overall-architecture.md` để xem tám sơ đồ kiến trúc.
3. `docs/susep/*` và `reports/checkpoints/P1-SUSEP-*` cho Track A.
4. `docs/ml/ml-data-contract.md` và `reports/checkpoints/P1-ML-*` cho Track B.
5. `P1-ORCH-*`, `P1-E2E-*`, `reports/final-project-report.md` cho evidence cuối.

## Năm nguyên tắc phải nhớ

1. Nhiều track có thể cùng canonical trong phạm vi của chúng.
2. Không có proven key thì không join.
3. Raw là immutable; sửa raw để test là phá evidence.
4. Static pass khác runtime pass.
5. Khi không có toolchain BI, nói `BLOCKED_MANUAL`; đừng giả completion.
