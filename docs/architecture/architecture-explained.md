# Kiến trúc hiện hành của Insurance Data Platform là gì?

Project có hai canonical source đang hoạt động theo hai track độc lập: SUSEP cho Market DWH/Performance và brvehins1 cho Motor Risk/ML. `canonical` ở đây giống “nguồn chuẩn của quầy hàng”: nó áp dụng trong đúng track, không biến một dataset thành chủ nhân của toàn repository.

```text
Track A — SUSEP: raw market CSV → `stg.SusepInsuranceMarket` → market DWH → DQ → performance
                                      → Performance Tuning / Market BI

Track B — brvehins1: raw CSV → stg.BrVehIns1 → dimensions + FactRiskObservation
                                      → DQ → bounded ML → RiskObservationPrediction
```

SUSEP và brvehins1 không có proven row-level relationship. Không tạo `CustomerId`, `PolicyId` hoặc mapping giả để nối chúng. Điều này không hạn chế hai track cùng chạy trên SQL Server hay cùng được Airflow điều phối độc lập; nó chỉ bảo vệ grain và tính trung thực của dữ liệu.

## Track B đã chứng minh những gì?

Track B là implementation runtime-validated: năm brvehins1 partitions đã vào `stg.BrVehIns1`; `DimDriverProfile`, `DimVehicle`, `DimGeography` và `FactRiskObservation` đã reconcile 1,965,355 rows; DQ production pass. ML đã train/score một deterministic bounded population đúng theo contract, không phải future customer/policy prediction. Chi tiết ở [dwh-design.md](dwh-design.md) và [../ml/ml-data-contract.md](../ml/ml-data-contract.md).

## Track A được xây dựa trên cái gì?

CSV SUSEP có các field market-level thực tế: company, `year_month`, product, state, premiums, claims và `claim_premium_ratio`. Nó là `ACTIVE_CANONICAL` của Track A. P1-SUSEP-01..05 đã có runtime evidence cho full-file contract, staging, one-observation fact, raw-to-fact reconciliation và DQ; xem [source-data-contract](../susep/source-data-contract.md).

## Các file SQL lịch sử có ý nghĩa gì?

Scaffold `Dim_Customer`, `Dim_Policy`, `Fact_Premium`/`Fact_Claims` và SCD2 cũ không phải evidence để chạy Track A hay Track B. Chúng được giữ như lịch sử và đánh dấu `STALE_SCAFFOLD`; model SUSEP hiện hành đã xuất phát từ CSV thật, không từ comment cũ. Historical reports vẫn giữ nguyên số liệu theo thời điểm được tạo.

## Tôi nên đọc tiếp ở đâu?

Đọc [project-scope.md](project-scope.md), rồi [source-strategy.md](source-strategy.md). Khi muốn hiểu implementation đang chạy, đi theo Track A (`docs/susep/`) hoặc Track B (`source-data-contract.md` → `staging-design.md` → `dwh-design.md` → `docs/ml/ml-data-contract.md`).
