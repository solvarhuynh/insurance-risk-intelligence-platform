# Insurance Data Platform

## Data Warehouse, Performance Tuning, Risk Analytics & Machine Learning

Project này được xây để chứng minh năng lực Data Engineering trên SQL Server, với trọng tâm Data Warehouse, ETL, Data Quality và Performance Tuning, sau đó mở rộng thêm Risk Analytics và Machine Learning.

Repository có nhiều **analytical track** — các luồng phân tích riêng trong cùng business domain bảo hiểm. Dùng cùng platform không có nghĩa dữ liệu của chúng có thể join theo từng row.

## Project có những track nào?

| Track | Canonical source | Mục đích | Trạng thái hiện tại |
|---|---|---|---|
| A — SUSEP Market | **data/raw/susep.gov.br/insurance_dataset.csv** | Market DWH, Performance Tuning, Market Power BI | RUNTIME_PASS: EDA → staging → market DWH → reconciliation → DQ; performance indexes có evidence |
| B — brvehins1 Motor Risk | **data/raw/brvehins1/brvehins1[a-e].csv** | Motor risk DWH, risk analytics, bounded ML | RUNTIME_PASS trong boundary Track B |
| C — Prudential Life Underwriting | Không có file physical | Future underwriting analytics | ORIGINAL_PLANNED_SOURCE / NOT_PRESENT |

SUSEP và brvehins1 đều là ACTIVE_CANONICAL trong track của mình. Prudential là ý định nguồn gốc, không phải dependency hiện tại.

## Vì sao không được join hai track active?

**Row identity** — căn cước của một dòng — chỉ tồn tại khi source có key/relationship thật. SUSEP là market observation theo company/time/product/state; brvehins1 là aggregate motor-risk observation. Không có customer, policy hay source mapping được chứng minh giữa chúng.

Vì vậy không được tạo CustomerId, PolicyId, mapping hay fact chung giả. Hãy xem [source strategy](docs/architecture/source-strategy.md) trước khi thiết kế integration.

## Kiến trúc được tổ chức ra sao?

~~~mermaid
flowchart TB
    P[Insurance Data Platform]
    P --> A[Track A: SUSEP Market DWH]
    P --> B[Track B: brvehins1 Motor Risk / ML]
    P -. planned .-> C[Track C: Prudential Life Underwriting]

    A --> A1[Market staging → market DWH → DQ]
    A1 --> A2[Performance Tuning / Market BI]
    B --> B1[stg.BrVehIns1 → risk DWH → DQ]
    B1 --> B2[Bounded ML → RiskObservationPrediction]

    O[Airflow orchestration boundary] -. điều phối từng track .-> A
    O -. điều phối từng track .-> B
~~~

Airflow đã chạy runtime hai nhánh độc lập: SUSEP ingest → DWH → reconciliation → DQ và brvehins1 foundation → DQ → scoring → prediction reconciliation. Power BI semantic model/handoff đã hoàn tất, nhưng dashboard `.pbix`/refresh thật cần Power BI Desktop hoặc PBIP toolchain nên được đánh dấu `BLOCKED_MANUAL`, không bị giả lập.

## Các track đã chạy thật đến đâu?

- **Track A — SUSEP:** 8.338.214 source rows = staging rows = market fact rows; premium/claims source→staging→fact reconcile; production DQ 14 hard rules PASS; hai query performance giảm logical reads khoảng 98,8–98,9% sau index có bằng chứng.

- Năm brvehins1 partition đã ingest vào **stg.BrVehIns1**.
- **DimDriverProfile**, **DimVehicle**, **DimGeography** và **FactRiskObservation** đã reconcile 1,965,355 rows.
- Production DQ gate đã pass.
- **claim_risk_model_v001** là cross-sectional HasClaim association trên population deterministic 100,004 rows; nó không dự đoán claim tương lai của customer/policy.
- Batch scoring held-out 20,000 rows vào **dwh.RiskObservationPrediction** đã reconcile difference 0 và rerun idempotent.

Evidence runtime theo stage nằm trong `reports/checkpoints/`. Không một kết quả Track A/Track B nào là bằng chứng cho row-level relationship với track còn lại.

## Tôi nên bắt đầu đọc ở đâu?

1. [Project scope](docs/architecture/project-scope.md) để hiểu các track và quy tắc không fake join.
2. [Source strategy](docs/architecture/source-strategy.md) để xem CSV thật, status và boundary giữa các source.
3. [Final learning guide](FINAL_PROJECT_GUIDE.md) để đọc theo hướng người mới.
4. Với implementation chạy thật: Track A contract → staging → market DWH; Track B contract → risk DWH → ML contract.
5. Với lịch sử: file trong **reports/checkpoints/** và **reports/** là evidence theo thời điểm tạo, không phải kiến trúc hiện hành.

## Tôi kiểm tra repository như thế nào?

~~~powershell
.\.venv\Scripts\python.exe scripts\validate_repo.py
$pythonFiles = @(Get-ChildItem scripts -Filter *.py -File | ForEach-Object FullName) + @(Get-ChildItem ml -Filter *.py -File | ForEach-Object FullName) + @((Resolve-Path dags\insurance_dwh_pipeline.py))
& .\.venv\Scripts\python.exe -m py_compile $pythonFiles
docker compose config
git diff --check
~~~

Validator chỉ là **static validation**: nó kiểm tra file, header, syntax và cấu trúc. Nó không chứng minh SQL Server/DQ/ML runtime. Xem [run guide](docs/guides/how-to-run.md), [final report](reports/final-project-report.md) và checkpoints để phân biệt evidence runtime với static check.

## Roadmap đi tiếp theo hướng nào?

~~~text
P1-ARCH-REALIGN-01
        ↓
P1-SUSEP-01 … P1-SUSEP-05
        ↓
P1-PERF-01 … P1-PERF-03
        ↓
P1-ORCH-01 / P1-ORCH-02
        ↓
P1-BI-01 … P1-BI-03
        ↓
P1-E2E-* → P1-DOC-*
~~~

Chi tiết milestones và ranh giới implementation nằm tại [roadmap](docs/specs/roadmap.md).
