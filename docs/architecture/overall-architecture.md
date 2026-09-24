# Kiến trúc hiện hành — Insurance Data Platform

Tài liệu này mô tả kiến trúc **đang vận hành**, không phải scaffold lịch sử. Platform có hai data track độc lập theo grain và source identity. Chúng chia sẻ hạ tầng SQL Server/Airflow, nhưng không có join theo từng dòng.

## 1. Overall multi-track architecture

```mermaid
flowchart TB
    P[Insurance Data Platform]
    P --> A[Track A — SUSEP Market DWH / Performance]
    P --> B[Track B — brvehins1 Motor Risk / ML]
    P -. planned source only .-> C[Track C — Prudential Underwriting]
    O[Airflow] -. orchestrates independently .-> A
    O -. orchestrates independently .-> B
    A --> AM[Market semantic subject area]
    B --> BM[Risk / ML semantic subject area]
    AM -.- N[No cross-track relationship]
    BM -.- N
```

`No cross-track relationship` là một quy tắc dữ liệu, không phải thiếu sót kỹ thuật. SUSEP là quan sát thị trường; brvehins1 là quan sát rủi ro motor tổng hợp. Không source nào chứng minh customer, policy hay event key chung.

## 2. Track A — SUSEP flow

```mermaid
flowchart LR
    R[Raw insurance_dataset.csv<br/>immutable] --> I[Python streaming ingestion]
    I --> S[stg.SusepInsuranceMarket<br/>batch + source lineage]
    S --> D[DimSusepMonth / Company / Product / State]
    D --> F[dwh.FactSusepInsuranceMarket<br/>company-month-product-state]
    S --> F
    F --> Q[Direct source → staging → fact reconciliation]
    Q --> G[dq.sp_RunSusepQualityGate]
    G --> T[Measured SQL workloads / indexes]
    G --> M[Insurance Market BI subject area]
```

Loader fingerprints source file and skips an already successful source version. DWH load only inserts an unseen stage row. Vì vậy rerun không nhân bản dữ liệu.

## 3. Track B — brvehins1 flow

```mermaid
flowchart LR
    R[Five immutable brvehins1 CSV partitions] --> S[stg.BrVehIns1]
    S --> D[DimDriverProfile / DimVehicle / DimGeography]
    D --> F[dwh.FactRiskObservation]
    S --> F
    F --> Q[dq.sp_RunQualityGate]
    Q --> X[bounded held-out scoring only]
    X --> P[dwh.RiskObservationPrediction]
    P --> V[Prediction reconciliation]
    V --> M[Motor Risk / ML BI subject area]
```

ML không phải retraining thường kỳ trong DAG. Nó reload artifact đã xác nhận, score population held-out theo contract, rồi kiểm tra technical identity.

## 4. SUSEP star schema

```mermaid
erDiagram
    DimSusepMonth ||--o{ FactSusepInsuranceMarket : SusepMonthKey
    DimSusepCompany ||--o{ FactSusepInsuranceMarket : SusepCompanyKey
    DimSusepProduct ||--o{ FactSusepInsuranceMarket : SusepProductKey
    DimSusepState ||--o{ FactSusepInsuranceMarket : SusepStateKey
    DimSusepMonth { int SusepMonthKey PK date YearMonth UK }
    DimSusepCompany { int SusepCompanyKey PK int CompanyCode UK string CompanyName }
    DimSusepProduct { int SusepProductKey PK string Product UK }
    DimSusepState { smallint SusepStateKey PK string State UK }
    FactSusepInsuranceMarket { bigint FactSusepInsuranceMarketKey PK bigint SusepStageRowId UK decimal Premiums decimal Claims }
```

Một fact là một `company_code + year_month + product + state` observation. `Premiums` và `Claims` được lưu chung vì đến từ cùng grain. Source ratio là non-additive; BI phải derive ratio từ tổng Claims/Premiums thay vì cộng ratio nguồn.

## 5. brvehins1 star schema

```mermaid
erDiagram
    DimDriverProfile ||--o{ FactRiskObservation : DriverProfileKey
    DimVehicle ||--o{ FactRiskObservation : VehicleKey
    DimGeography ||--o{ FactRiskObservation : GeographyKey
    FactRiskObservation ||--o{ RiskObservationPrediction : technical_identity
    DimDriverProfile { int DriverProfileKey PK string Gender int DrivAge }
    DimVehicle { int VehicleKey PK int VehYear string VehModel string VehGroup }
    DimGeography { int GeographyKey PK string Area string StateAb }
    FactRiskObservation { bigint RiskObservationKey PK string SourceFile int SourceRowNumber UK decimal ExposTotal decimal PremTotal int TotalClaimCount }
    RiskObservationPrediction { bigint RiskObservationPredictionKey PK string ScoringPopulation string ModelVersion float PredictedProbability }
```

Quan hệ prediction dùng identity kỹ thuật đã có trong contract Track B. Nó không tạo customer-level entity hoặc future-policy prediction.

## 6. Airflow DAG runtime

```mermaid
flowchart TB
    S[platform_start]
    S --> A1[Track A ingest]
    A1 --> A2[Track A DWH]
    A2 --> A3[Track A reconciliation]
    A3 --> A4[Track A DQ]
    A4 --> A5[Track A market consumer ready]
    S --> B1[Track B foundation precheck]
    B1 --> B2[Track B incremental audit]
    B2 --> B3[Track B DQ]
    B3 --> B4[Track B batch score]
    B4 --> B5[Track B prediction reconciliation]
    B5 --> B6[Track B risk consumer ready]
```

Hai nhánh không được nối bằng dependency giả. Khi Track A DQ fail, chỉ downstream Track A bị chặn; Track B tiếp tục theo policy độc lập của DAG.

## 7. ML lifecycle — Track B only

```mermaid
flowchart LR
    C[FactRiskObservation + dimensions] --> E[Contract-controlled extraction]
    E --> P[Deterministic bounded population]
    P --> S[Group-safe train / validation / held-out test split]
    S --> A[claim_risk_model_v001.joblib + metadata]
    A --> R[Reload under scikit-learn 1.7.2]
    R --> B[Batch score 20,000 held-out rows]
    B --> Q[Prediction identity reconciliation]
```

Artifact biểu diễn cross-sectional association với `HasClaim`, không phải claim probability tương lai cho customer/policy.

## 8. Docker/runtime architecture

```mermaid
flowchart TB
    H[Host repository + .env credentials] --> C[Docker Compose]
    C --> SQL[SQL Server 2022<br/>DWH_Insurance]
    C --> AF[Airflow standalone profile]
    AF --> SQL
    AF --> RAW[Raw files mounted read-only]
    AF --> CODE[Scripts + ML mounted read-only]
    AF --> REP[Reports mounted writable]
    DEV[Host .venv<br/>scikit-learn 1.7.2] --> SQL
    DEV --> ART[ML artifact reload]
```

Airflow chạy bằng Docker image riêng; host `.venv` dùng dependency ML đã pin cho artifact. Raw mounts đều read-only và không được mutation bởi runtime nào.
