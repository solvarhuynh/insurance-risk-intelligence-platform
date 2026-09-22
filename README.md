# Insurance DWH, Performance Tuning & Machine Learning

Dự án cá nhân — Data Engineering & Machine Learning trên nền tảng Microsoft SQL Server, ứng dụng dữ liệu bảo hiểm thật quy mô lớn (~10 triệu dòng, ~2.5 GB raw), tích hợp mô hình dự đoán rủi ro (Batch ML Scoring) và lớp phân tích Power BI. Trọng tâm của dự án là chứng minh năng lực thiết kế Data Warehouse chuẩn mực, viết ETL bằng T-SQL với CDC, tối ưu hóa hiệu năng (Performance Tuning) trên dữ liệu lớn, và xây dựng pipeline dự đoán tự động bằng Apache Airflow.
Dự án cá nhân — Data Engineering & Machine Learning trên nền tảng Microsoft SQL Server, ứng dụng bộ dữ liệu bảo hiểm xe cơ giới Brazil thật (**brvehins1** từ hệ sinh thái CASdatasets / AUTOSEG / SUSEP, quy mô ~1.965 triệu dòng, 5 phân đoạn CSV ~302 MB raw), tích hợp luồng dự đoán rủi ro (Batch ML Scoring) và lớp phân tích Power BI. Trọng tâm của dự án là chứng minh năng lực thiết kế Motor Insurance Data Warehouse chuẩn mực, viết ETL bằng T-SQL với CDC, tối ưu hóa hiệu năng (Performance Tuning) trên dữ liệu lớn, và xây dựng pipeline tự động hóa bằng Apache Airflow.

## Mục tiêu dự án

- Thiết kế và xây dựng hệ thống Data Warehouse chuyên nghiệp phục vụ ngành Bảo hiểm nhân thọ và phi nhân thọ, bám sát các yêu cầu thực tế của hệ sinh thái Microsoft (SQL Server, T-SQL, SSIS).
- Thiết kế và xây dựng hệ thống Data Warehouse chuyên nghiệp phục vụ ngành Bảo hiểm xe cơ giới (Motor Insurance), bám sát các yêu cầu thực tế của hệ sinh thái Microsoft (SQL Server, T-SQL, SSIS/Airflow).
- Mô hình hóa kho dữ liệu xoay quanh các thực thể và thước đo nghiệp vụ thực tế có trong dữ liệu: Hồ sơ người lái (Driver Profile: Gender, DrivAge), Phương tiện (Vehicle: VehYear, VehModel, VehGroup), Địa lý (Geography: State, StateAb, Area), Thời gian chịu rủi ro (Exposure: ExposTotal, ExposFireRob), Doanh thu phí (Premium: PremTotal, PremFireRob), Giá trị bảo hiểm (SumInsAvg), và Tổn thất bồi thường (Claims: ClaimNb*, ClaimAmount* theo từng loại rủi ro: Robbery, Partial Collision, Total Collision, Fire, Other).
- Xây dựng luồng ETL bằng T-SQL với khả năng Incremental Load dựa trên Change Data Capture (CDC) và cơ chế lưu vết Watermark, giúp tiết kiệm tài nguyên so với full reload.
- Thiết kế cơ chế Audit Log đầy đủ và tính idempotent, đảm bảo chạy lại cùng batch không gây trùng lặp hoặc sai lệch dữ liệu.
- Áp dụng SCD Type 2 cho bảng chiều khách hàng (Dim_Customer) để theo dõi lịch sử thay đổi thông tin theo thời gian trên tập dữ liệu ~1.5 triệu khách hàng.
- Xây dựng framework Data Quality tự động kiểm định toàn vẹn dữ liệu (Not Null, Unique, Referential Integrity, Business Rules) và chủ động ngắt pipeline khi phát hiện lỗi critical.
- Tích hợp mô hình Machine Learning dự đoán xác suất rủi ro tổn thất (Claim Occurrence Probability / Risk Scoring), sử dụng DWH như một Feature Store và tự động hóa batch scoring qua Airflow.
- Tích hợp mô hình Machine Learning dự đoán rủi ro tổn thất xe cơ giới (Claim Frequency / Claim Severity / Loss Propensity), sử dụng DWH như một Feature Store và tự động hóa batch scoring qua Airflow.
- Điều phối toàn bộ pipeline qua Apache Airflow trên môi trường Docker hóa.
- Chứng minh năng lực Performance Tuning bằng cách đo lường, so sánh Execution Plan và chỉ số STATISTICS IO/TIME trước và sau khi tối ưu hóa bằng Indexing.
- Xây dựng dashboard Power BI trực quan hóa chỉ số nghiệp vụ (Loss Ratio, xu hướng phí bảo hiểm) và đối chiếu rủi ro dự đoán với thực tế.
- Chứng minh năng lực Performance Tuning bằng cách đo lường, so sánh Execution Plan và chỉ số STATISTICS IO/TIME trước và sau khi tối ưu hóa bằng Indexing trên tập dữ liệu ~2 triệu dòng.
- Xây dựng dashboard Power BI trực quan hóa chỉ số nghiệp vụ (Loss Ratio, Claim Frequency, mức độ rủi ro theo vùng miền và dòng xe).

## Nguồn dữ liệu

| Bộ dữ liệu | Nguồn | Quy mô | Vai trò trong dự án |
|---|---|---|---|
| Brazilian Insurance Market Data (SUSEP) | Kaggle / susep.gov.br — dataset công khai do cơ quan quản lý bảo hiểm Brazil (SUSEP) công bố | ~8.3 triệu dòng, dữ liệu thật từ 2003, cập nhật theo quý (~1.5 GB CSV) | Nguồn chính cho Fact_Premium / Fact_Claims — phí, bồi thường theo công ty, sản phẩm, bang, tháng |
| Porto Seguro's Safe Driver Prediction | Kaggle competition — dữ liệu bảo hiểm xe cơ giới Brazil thật | ~1.5 triệu dòng, 57 features đặc trưng nhân khẩu, xe và tổn thất (~500 MB CSV) | Nguồn cho Dim_Customer, Feature Store và huấn luyện mô hình Machine Learning dự đoán rủi ro |
| Bộ dữ liệu | Đường dẫn trong repo | Quy mô | Vai trò trong dự án | Trạng thái |
|---|---|---|---|---|
| **brvehins1 (Canonical Dataset)** | `data/raw/brvehins1/brvehins1[a-e].csv` | 1.965.355 dòng, 23 cột (~302 MB CSV chia làm 5 phân đoạn) | Dữ liệu nguồn duy nhất (Canonical Source) cho toàn bộ pipeline DWH, ETL, Staging, ML Feature Store và Power BI | **CANONICAL (Có sẵn trong repo)** |
| susep.gov.br Market Data | `data/raw/susep.gov.br/insurance_dataset.csv` | 1 file CSV (~751 MB) | Báo cáo thị trường bảo hiểm vĩ mô tổng hợp của SUSEP giai đoạn trước | **LEGACY / NON-CANONICAL (Lưu trữ lịch sử, không dùng trong pipeline)** |

Hai bộ dữ liệu cùng bắt nguồn từ thị trường bảo hiểm Brazil, mang lại sự đồng nhất cao về bối cảnh địa lý và kinh tế. Tổng quy mô thô đạt **~2.0 — 2.5 GB CSV** (~10 triệu dòng), khi nạp vào SQL Server kèm Staging, CDC và Indexing sẽ đạt **~5 — 6 GB database**.
> Lưu ý quan trọng về dữ liệu:
> 1. Bộ dữ liệu canonical của dự án gồm 5 phân đoạn bất biến: `brvehins1a.csv`, `brvehins1b.csv`, `brvehins1c.csv`, `brvehins1d.csv`, `brvehins1e.csv` trong thư mục `data/raw/brvehins1/`. Cả 5 file đều có cùng schema 23 cột, mỗi file chứa 393.071 dòng dữ liệu.
> 2. File `data/raw/susep.gov.br/insurance_dataset.csv` là dữ liệu cũ được giữ lại để bảo toàn lịch sử nghiên cứu, không thuộc luồng dữ liệu canonical và không tham gia vào pipeline hiện tại.
> 3. Kiến trúc trước đây scaffold cho SUSEP + Porto Seguro đã bị loại bỏ. Dự án chỉ sử dụng dataset canonical brvehins1 có sẵn trong repo.

## Kiến trúc tổng quan (Kiến trúc mục tiêu)

Mô hình mục tiêu mô tả luồng dữ liệu End-to-End dự kiến khi hoàn thành toàn bộ 8 giai đoạn:
Staging -> DWH Star Schema -> Incremental Load/CDC -> Data Quality -> Machine Learning Batch Scoring -> Orchestration Airflow -> Performance Tuning -> Power BI.
Staging (5 phân đoạn brvehins1) -> DWH Star Schema -> Incremental Load/CDC -> Data Quality -> Machine Learning Batch Scoring -> Orchestration Airflow -> Performance Tuning -> Power BI.

1. Staging: Nạp file CSV thô vào database Staging_InsuranceRaw bằng lệnh BULK INSERT, giữ nguyên cấu trúc ban đầu để đối chiếu toàn vẹn.
2. DWH Star Schema: Fact_Premium, Fact_Claims, Fact_Customer_Risk_Prediction (bảng sự kiện); Dim_Customer (SCD Type 2), Dim_Policy, Dim_Date, Dim_Region (bảng chiều).
3. Incremental Load / CDC: T-SQL Stored Procedures dùng lệnh MERGE để UPSERT; bật SQL Server Change Data Capture (CDC) trên Staging để chỉ nạp phần dữ liệu mới/thay đổi, không reload toàn bộ mỗi lần.
4. Data Quality: Bộ kiểm định tự động (not null, unique, referential integrity) chạy như một bước trong pipeline, ghi log vào DQ_Check_Log, làm pipeline dừng và cảnh báo nếu không đạt.
5. Machine Learning Batch Scoring: Script Python đọc feature từ DWH, tính toán xác suất phát sinh bồi thường (`PredictedClaimProbability`, `RiskCategory`) và nạp ngược kết quả vào `Fact_Customer_Risk_Prediction`.
1. Staging: Nạp 5 phân đoạn CSV thô vào database `Staging_InsuranceRaw` bằng lệnh `BULK INSERT`, giữ nguyên cấu trúc 23 cột ban đầu để đối chiếu toàn vẹn.
2. DWH Star Schema: Các bảng chiều (Dim_Driver, Dim_Vehicle, Dim_Geography) và bảng sự kiện (Fact_Policy_Exposure, Fact_Claims, Fact_Risk_Prediction).
3. Incremental Load / CDC: T-SQL Stored Procedures dùng lệnh `MERGE` để UPSERT; bật SQL Server Change Data Capture (CDC) trên Staging để chỉ nạp phần dữ liệu mới/thay đổi, không reload toàn bộ mỗi lần.
4. Data Quality: Bộ kiểm định tự động (not null, unique, referential integrity, positive amounts) chạy như một bước trong pipeline, ghi log vào `DQ_Check_Log`, làm pipeline dừng và cảnh báo nếu không đạt.
5. Machine Learning Batch Scoring: Script Python đọc feature từ DWH, tính toán xác suất phát sinh bồi thường / mức độ rủi ro và nạp ngược kết quả vào bảng dự đoán rủi ro trong DWH.
6. Orchestration Airflow: Apache Airflow điều phối toàn bộ DAG: Load Staging -> Load Dim (song song) -> Load Fact -> Data Quality Check -> ML Batch Scoring -> Load Predictions -> Notify.
7. Performance Tuning: Đo trước và sau bằng Execution Plan + STATISTICS IO/TIME trên bảng Fact ~8-10 triệu dòng, thêm Non-Clustered/Covering Index, cân nhắc partitioning theo tháng.
8. Power BI: Kết nối trực tiếp DWH, xây dashboard loss ratio, xu hướng phí, và đối chiếu rủi ro dự đoán của mô hình AI với tổn thất thực tế.
7. Performance Tuning: Đo trước và sau bằng Execution Plan + STATISTICS IO/TIME trên bảng Fact ~2 triệu dòng, thêm Non-Clustered/Covering Index, cân nhắc partitioning.
8. Power BI: Kết nối trực tiếp DWH, xây dashboard Loss Ratio theo bang/khu vực, dòng xe, độ tuổi lái xe, và đối chiếu rủi ro dự đoán của mô hình AI với tổn thất thực tế.

## Công nghệ sử dụng

| Hạng mục | Công cụ |
|---|---|
| Cơ sở dữ liệu | Microsoft SQL Server (Docker trên WSL) |
| Ngôn ngữ chính | T-SQL (ETL, tuning), Python (nạp dữ liệu, Machine Learning, DAG Airflow) |
| Incremental Load | SQL Server Change Data Capture (CDC) |
| Orchestration | Apache Airflow (chạy trong Docker) |
| Machine Learning | scikit-learn, LightGBM (huấn luyện và batch scoring) |
| Schema Migration | Flyway hoặc DbUp — quản lý schema theo version |
| Data Quality | dbt tests / Great Expectations / T-SQL DQ Stored Procedures |
| Data Quality | T-SQL DQ Stored Procedures & DQ_Check_Log |
| Công cụ quản trị DB | Azure Data Studio / SSMS |
| Trực quan hoá | Power BI Desktop |
| Quản lý mã nguồn & tài liệu | Git/GitHub, README có ảnh chụp Execution Plan |
| Quản lý mã nguồn & kiểm tra | Git/GitHub, Python static validation script (`scripts/validate_repo.py`) |

## Cấu trúc repo

```
insurance-dwh-project/
├── .cursor/
│   └── rules/
├── .gitignore
├── data/raw/
│   └── .gitkeep
├── data/
│   └── raw/
│       ├── brvehins1/          # CANONICAL SOURCE: 5 phân đoạn CSV (~1.965M dòng)
│       │   ├── brvehins1a.csv
│       │   ├── brvehins1b.csv
│       │   ├── brvehins1c.csv
│       │   ├── brvehins1d.csv
│       │   └── brvehins1e.csv
│       └── susep.gov.br/       # LEGACY SOURCE: Không sử dụng trong pipeline canonical
│           └── insurance_dataset.csv
├── docs/
│   ├── architecture/
│   │   ├── architecture-explained.md
│   │   ├── data-dictionary.md
│   │   └── repository-structure.md
│   ├── guides/
│   │   ├── glossary.md
│   │   └── how-to-run.md
│   ├── reports/
│   │   ├── insights.md
│   │   └── performance-tuning-summary.md
│   └── specs/
│       ├── implementation-guide.md
│       └── insurance-dwh-overview.pdf
├── ml/
│   ├── train_risk_model.py
│   └── predict_risk_batch.py
├── dags/
│   └── insurance_dwh_pipeline.py
├── log/
│   ├── progress-log.md
│   └── review-report-2026-09-15.md
├── migrations/
│   └── V1__create_dwh_schema.sql
├── notebooks/
│   └── 01-eda.ipynb
├── powerbi/
│   └── .gitkeep
├── scripts/
│   └── validate_repo.py
├── sql/
│   ├── 01_load_staging.sql
│   ├── 02_enable_cdc.sql
│   ├── 03_sp_dim_customer_scd2.sql
│   ├── 04_sp_dim_others.sql
│   ├── 05_sp_fact_premium.sql
│   ├── 06_sp_fact_claims.sql
│   ├── 07_data_quality_checks.sql
│   └── 08_sp_load_risk_predictions.sql
├── docker-compose.yml
└── README.md
```

## Cách chạy dự án

Lưu ý: Dự án hiện đang ở Giai đoạn 1. Các bước dưới đây mô tả trình tự thực thi theo thiết kế mục tiêu, kèm trạng thái kiểm tra thực tế hiện tại của từng bước:
Lưu ý: Dự án hiện đang ở Giai đoạn 1 (Khảo sát & chuẩn bị dữ liệu thật). Các script trong `sql/`, `migrations/`, `ml/`, `dags/` đang là khung mẫu khởi tạo từ kiến trúc cũ, được gắn nhãn `STALE SCAFFOLD` và sẽ được tái cấu trúc (refactor) theo Data Contract của `brvehins1` trong các task kỹ thuật tiếp theo.

### Bước 1: Thiết lập hạ tầng Docker
- Trạng thái: STATIC_PASS (tệp `docker-compose.yml` đã được kiểm tra cú pháp hợp lệ; chưa chạy container runtime).
- Khởi chạy container SQL Server và Airflow:
### Bước 1: Kiểm tra tĩnh toàn bộ repository
- Chạy script kiểm tra baseline tĩnh (xác thực tệp bắt buộc, cấu trúc 5 phân đoạn `brvehins1`, parse Compose, biên dịch Python và cú pháp SQL):
  ```bash
  docker-compose up -d
  python scripts/validate_repo.py
  ```

### Bước 2: Chạy Schema Migrations
- Trạng thái: SCAFFOLD (`migrations/V1__create_dwh_schema.sql` chứa DDL mẫu đang để dạng block comment, chưa áp dụng vào database qua Flyway/DbUp).
- Khởi tạo DWH schema (bao gồm 8 bảng Fact/Dim và bảng dự đoán ML) qua Flyway hoặc DbUp:
### Bước 2: Thiết lập hạ tầng Docker
- Trạng thái: STATIC_PASS (tệp `docker-compose.yml` đã kiểm tra cú pháp hợp lệ; chưa chạy container runtime).
- Khởi chạy container SQL Server và Airflow:
  ```bash
  # TODO: Chạy migration V1__create_dwh_schema.sql
  docker-compose up -d
  ```

### Bước 3: Nạp dữ liệu và Kích hoạt CDC
- Trạng thái: SCAFFOLD (chưa tải file CSV thô vào `data/raw/`; `sql/01_load_staging.sql` và `sql/02_enable_cdc.sql` đang là script khung).
- Chạy script nạp staging và bật CDC:
  ```bash
  # TODO: Chạy sql/01_load_staging.sql và sql/02_enable_cdc.sql
  ```
### Bước 3: Chạy Schema Migrations
- Trạng thái: STALE SCAFFOLD (`migrations/V1__create_dwh_schema.sql` đang là DDL mẫu cũ, cần refactor theo schema `brvehins1` trước khi áp dụng).

### Bước 4: Huấn luyện mô hình Machine Learning
- Trạng thái: STATIC_PASS (`ml/train_risk_model.py` vượt qua kiểm tra cú pháp `py_compile`; hàm trích xuất dữ liệu đang là stub chờ dữ liệu).
- Huấn luyện mô hình baseline tính điểm rủi ro:
  ```bash
  python ml/train_risk_model.py
  ```
### Bước 4: Nạp Staging brvehins1 và Kích hoạt CDC
- Trạng thái: STALE SCAFFOLD (`sql/01_load_staging.sql` và `sql/02_enable_cdc.sql` cần refactor theo 23 cột của `brvehins1`).

### Bước 5: Chạy pipeline trên Airflow
- Trạng thái: STATIC_PASS (`dags/insurance_dwh_pipeline.py` vượt qua kiểm tra cú pháp `py_compile`; các task hiện dùng operator stub, chưa chạy trên cụm Airflow thật).
- Kích hoạt DAG `insurance_dwh_pipeline` trên Airflow Webserver (`http://localhost:8080`).
- Pipeline sẽ tự động thực thi: Staging -> Dimensions -> Facts -> DQ Checks -> ML Batch Scoring -> Load Predictions -> Notify.
### Bước 5: Huấn luyện mô hình Machine Learning & Batch Scoring
- Trạng thái: STALE SCAFFOLD / PENDING DATA CONTRACT (`ml/train_risk_model.py` và `ml/predict_risk_batch.py` cần refactor logic trích xuất đặc trưng theo `brvehins1`).

### Bước 6: Chạy pipeline trên Airflow
- Trạng thái: STATIC_PASS / STALE SCAFFOLD (`dags/insurance_dwh_pipeline.py` hợp lệ cú pháp Python AST, các task đang dùng stub operator).

## Trạng thái triển khai hiện tại (Current Implementation Status)

Dự án hiện đang ở **Giai đoạn 1 — Khảo sát & chuẩn bị dữ liệu thật** (kết hợp hoàn thiện Governance và Validation Layer). Toàn bộ mã nguồn và kịch bản trong kho lưu trữ hiện ở mức **SCAFFOLD** hoặc **STATIC_PASS**, chưa có subsystem nào đạt **RUNTIME_PASS**.
Dự án hiện đang ở **Giai đoạn 1 — Khảo sát & chuẩn bị dữ liệu thật**. Dữ liệu thô canonical `brvehins1` (5 phân đoạn, ~1.965M dòng) đã có sẵn trong kho lưu trữ và vượt qua kiểm tra tĩnh. Toàn bộ mã nguồn SQL/ML/DAG hiện ở mức **STALE SCAFFOLD** hoặc **STATIC_PASS**, sẵn sàng cho task `P1-DATA-01 — Real EDA & Source Data Contract`.

### Quy ước trạng thái chuẩn
- `SCAFFOLD`: Mới tạo khung, template, stub, commented-out; chưa chạy.
- `STATIC_PASS`: Đã vượt qua kiểm tra cú pháp, compile, linter, parse tĩnh.
- `RUNTIME_PASS`: Đã thực thi thành công trong môi trường runtime thật với dữ liệu thật.
- `BLOCKED`: Đang bị nghẽn do thiếu dependency, dữ liệu hoặc hạ tầng.
- `DONE`: Milestone / task workflow hoàn tất trọn vẹn theo Definition of Done.
- `FAILED`: Chạy runtime hoặc validation bị lỗi.

### Bảng tổng hợp hiện trạng các phân hệ

| Phân hệ | Trạng thái hiện tại | Bằng chứng thực tế |
|---|---|---|
| Data/raw (SUSEP, Porto Seguro) | SCAFFOLD | Chỉ có `data/raw/.gitkeep`, chưa có file CSV thô |
| Data/raw (brvehins1) | STATIC_PASS | Đủ 5 phân đoạn `brvehins1[a-e].csv` (1.965.355 dòng, schema 23 cột đồng nhất) |
| Data/raw legacy (susep.gov.br) | LEGACY | File `insurance_dataset.csv` (~751 MB) được lưu trữ lịch sử, không dùng trong pipeline |
| Docker compose | STATIC_PASS | `docker-compose.yml` pass parse tĩnh; chưa khởi chạy container |
| Migrations (DDL V1) | SCAFFOLD | `migrations/V1__create_dwh_schema.sql` chứa DDL mẫu dạng block comment |
| Staging load | SCAFFOLD | `sql/01_load_staging.sql` chứa DDL và BULK INSERT stub dạng block comment |
| CDC | SCAFFOLD | `sql/02_enable_cdc.sql` chứa script bật CDC và bảng watermark stub |
| SCD2 (Customer) | SCAFFOLD | `sql/03_sp_dim_customer_scd2.sql` chứa procedure MERGE stub |
| Fact load (Premium, Claims) | SCAFFOLD | `sql/05_...` và `sql/06_...` chứa procedure MERGE stub |
| Data Quality check | SCAFFOLD | `sql/07_data_quality_checks.sql` chứa procedure kiểm tra stub |
| Migrations (DDL V1) | STALE SCAFFOLD | `migrations/V1__create_dwh_schema.sql` chứa DDL mẫu cũ; cần refactor theo brvehins1 |
| Staging load | STALE SCAFFOLD | `sql/01_load_staging.sql` chứa DDL mẫu cũ; cần refactor theo 23 cột brvehins1 |
| CDC | STALE SCAFFOLD | `sql/02_enable_cdc.sql` là kịch bản khung; cần refactor theo staging brvehins1 |
| Dimensions | STALE SCAFFOLD | `sql/03_...` và `sql/04_...` cần refactor theo các thực thể Driver, Vehicle, Geography |
| Facts | STALE SCAFFOLD | `sql/05_...` và `sql/06_...` cần refactor theo Exposure, Premium, Claims của brvehins1 |
| Data Quality check | STALE SCAFFOLD | `sql/07_data_quality_checks.sql` cần refactor theo các rule dữ liệu xe cơ giới |
| Airflow DAG | STATIC_PASS | `dags/insurance_dwh_pipeline.py` pass `py_compile`; task dùng stub operator |
| ML model training | STATIC_PASS | `ml/train_risk_model.py` pass `py_compile`; logic trích xuất dạng stub |
| ML batch scoring | STATIC_PASS / SCAFFOLD | `ml/predict_risk_batch.py` pass `py_compile`; `sql/08_...` chứa MERGE stub |
| Performance tuning | SCAFFOLD | Báo cáo `docs/reports/` là template cho Giai đoạn 7; chưa có script index/partition |
| ML model training | STATIC_PASS | `ml/train_risk_model.py` pass `py_compile`; logic trích xuất cũ chờ data contract mới |
| ML batch scoring | STATIC_PASS / STALE SCAFFOLD | `ml/predict_risk_batch.py` pass `py_compile`; `sql/08_...` chứa MERGE stub cũ |
| Performance tuning | SCAFFOLD | Báo cáo `docs/reports/` là template cho Giai đoạn 7; chờ dữ liệu thật trên DWH |
| Power BI dashboard | SCAFFOLD | Chỉ có `powerbi/.gitkeep`, chưa có file `.pbix` |

Chi tiết nhật ký công việc và kế hoạch từng bước được cập nhật liên tục tại [log/progress-log.md](log/progress-log.md).

## Ghi chú về Performance Tuning

Chứng minh năng lực tối ưu hóa bằng ảnh chụp Execution Plan trước và sau khi tạo Index trên Fact table ~8-10 triệu dòng, bảng so sánh chỉ số STATISTICS IO/TIME (logical reads, elapsed time) sẽ được trình bày chi tiết tại mục này sau khi hoàn thành Giai đoạn 7.
Chứng minh năng lực tối ưu hóa bằng ảnh chụp Execution Plan trước và sau khi tạo Index trên Fact table quy mô ~2 triệu dòng dữ liệu xe cơ giới, bảng so sánh chỉ số STATISTICS IO/TIME (logical reads, elapsed time) sẽ được trình bày chi tiết tại mục này sau khi hoàn thành Giai đoạn 7.
