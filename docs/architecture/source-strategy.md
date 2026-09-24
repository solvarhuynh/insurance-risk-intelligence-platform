# Chiến lược nguồn dữ liệu hiện hành

`ACTIVE_CANONICAL` được hiểu theo **data track**. Không có source canonical duy nhất cho toàn Insurance Data Platform.

| Source | Physical path | Track / purpose | Current evidence |
|---|---|---|---|
| SUSEP market | `data/raw/susep.gov.br/insurance_dataset.csv` | A — Market DWH, DQ, performance, Market BI | EDA/staging/DWH/reconciliation/DQ/performance `RUNTIME_PASS`; BI artifact `BLOCKED_MANUAL` |
| brvehins1, 5 partitions | `data/raw/brvehins1/brvehins1[a-e].csv` | B — Motor risk DWH, risk analytics, bounded ML | staging/DWH/DQ/artifact/scoring `RUNTIME_PASS` |
| Prudential Life Insurance Assessment | Not present | C — future underwriting only | `ORIGINAL_PLANNED_SOURCE / NOT_PRESENT / FUTURE` |

## Track A — SUSEP facts

SUSEP raw có 751.126.569 bytes, 8.338.214 rows và 8 cột: `company_code`, `company_name`, `year_month`, `product`, `state`, `premiums`, `claims`, `claim_premium_ratio`. Grain đã xác minh là `company_code + year_month + product + state`.

Một row là market observation. Nó không chứng minh customer, policy, claim event, VIN hay exposure entity. Source contract và semantic uncertainty: `docs/susep/source-data-contract.md`.

Target implementation hiện hành là `stg.SusepInsuranceMarket` → bốn SUSEP dimension → `dwh.FactSusepInsuranceMarket`. Fact giữ một accepted stage row và source/batch lineage. Premium/claims reconcile source→staging→fact; source ratio là non-additive.

## Track B — brvehins1 facts

brvehins1 gồm năm schema 23 cột, tổng 1.965.355 rows. Một row là aggregate motor-risk observation; `SourceFile + SourceRowNumber` là technical identity. Target warehouse là dimensions driver/vehicle/geography và `dwh.FactRiskObservation`; ML/prediction là consumer Track B riêng.

Chi tiết contract ở `docs/architecture/source-data-contract.md`; ML semantic ở `docs/ml/ml-data-contract.md`.

## Integration được phép và bị cấm

| Track | Được phép | Bị cấm |
|---|---|---|
| A — SUSEP | SQL Server, Track-A DQ/Airflow, performance, Market subject area | join row-level với B/C; customer/policy/claim event giả |
| B — brvehins1 | SQL Server, Track-B DQ/Airflow, ML, Risk subject area | score SUSEP/Prudential bằng model B; biến fact B thành fact platform |
| C — Prudential | inventory/EDA/contract độc lập khi raw xuất hiện | auto-download; `Dim_Customer` hoặc join trước proven relationship |

Airflow điều phối hai route nhưng không tạo data relationship. Power BI có hai subject area/page disconnected; không có cross-filter/bridge giữa A và B.

## Prudential khi source xuất hiện

Khi và chỉ khi raw xuất hiện hợp pháp trong workspace, Track C phải qua inventory → EDA → source contract → thiết kế riêng. Chỉ một key/relationship được chứng minh bằng source mới mở quyền cân nhắc integration. Không lấy scaffold `Dim_Customer` cũ làm evidence.

## Historical scope drift

Một số historical reports/log nói SUSEP legacy hoặc brvehins1 canonical duy nhất. Chúng được giữ nguyên cho audit theo thời điểm; không phải source of truth hiện hành. Current source of truth là README, scope, tài liệu này, overall architecture và final report.
