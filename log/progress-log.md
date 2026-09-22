# Progress Log

Muc dich: ghi lai toan bo tien do du an theo thoi gian thuc, de bat ky AI hoac nguoi nao tiep tuc cong viec deu co the doc file nay va biet chinh xac da lam gi, tao file nao, o dau, con thieu gi.

## Cach dung
- Sau moi buoc hoan thanh (tao file, sua file, chay thanh cong mot script, hoan tat mot Definition of Done), them mot dong moi vao bang ben duoi.
- Khong xoa dong cu. Neu mot viec bi lam lai, ghi dong moi voi trang thai "Redo" va ly do.
- Truoc khi bat dau phien lam viec moi, doc toan bo bang nay truoc, uu tien doc tu duoi len de biet trang thai moi nhat.

## Quy uoc trang thai
- SCAFFOLD: Moi tao khung, stub, template, commented-out, chua co logic thuc thi hoan chinh hoac chua chay.
- STATIC_PASS: Da vuot qua kiem tra tinh (linter, syntax check, compile check, static import check, parse YAML/JSON).
- RUNTIME_PASS: Da chay thuc te thanh cong trong moi truong runtime that (Docker/SQL Server/Airflow/Python) voi input va output that.
- BLOCKED: Dang bi nghen do thieu dependency, thieu du lieu dau vao, hoac thieu ha tang.
- DONE: Chi dung khi mot milestone / task workflow hoan tat tron ven theo dung Definition of Done cua task do.
- FAILED: Chay runtime hoac validation bi loi, can sua chua.

QUY TAC BAT BUOC:
- Khong dung DONE de thay the cho SCAFFOLD.
- Trang thai DONE chi ap dung cho cac task workflow/quan tri hoac cac milestone ky thuat da dat toan bo tieu chi Definition of Done (bao gom validation tuong ung).

## Bang tien do

> Chu thich kiem toan (Audit Note / Semantics Note): Toan bo cac dong log lich su ben duoi co trang thai "Done" (tu 2026-09-15 den 2026-09-18) duoc giu nguyen ven de bao toan du lieu lich su. Cac dong nay phan anh viec hoan thanh tao khung cau truc (scaffold), script khoi tao hoac tai lieu dac ta, va PHAI duoc doc kem cot "Ghi chu" de hieu dung ngu canh. Cac dong nay KHONG dong nghia voi viec toan bo tinh nang hay pipeline da dat RUNTIME_PASS.

| Thoi gian | Giai doan | Viec da lam | File da tao/sua | Duong dan | Trang thai | Ghi chu |
|---|---|---|---|---|---|---|
| 2026-09-15 13:15 | Scaffold | Khoi tao file nhat ky tien do du an | progress-log.md | log/progress-log.md | Done | Tao khung file log theo quy dinh |
| 2026-09-15 13:15 | Scaffold | Tao file cau hinh bo qua git | .gitignore | .gitignore | Done | Loai tru data/raw/*, credentials, pycache, notebook checkpoints |
| 2026-09-15 13:16 | Giai doan 1 | Tao file giu cho thu muc du lieu tho | .gitkeep | data/raw/.gitkeep | Done | Thu muc luu CSV tho SUSEP va Prudential (khong commit du lieu lon) |
| 2026-09-15 13:16 | Giai doan 1 | Tao file giu cho thu muc tai lieu | .gitkeep | docs/.gitkeep | Done | Thu muc luu tai lieu du an (data-dictionary, erd, insights) |
| 2026-09-15 13:16 | Giai doan 1 | Tao notebook EDA khao sat du lieu | 01-eda.ipynb | notebooks/01-eda.ipynb | Done | San sang cac section: Load data, Shape & dtypes, Null check, Duplicate check, DQ issues |
| 2026-09-15 13:16 | Giai doan 2 | Tao docker-compose khoi tao ha tang | docker-compose.yml | docker-compose.yml | Done | Cau hinh 2 service: SQL Server 2022 va Airflow (webserver + scheduler), RAM >= 6GB |
| 2026-09-15 13:16 | Giai doan 2 | Tao script nap staging bang BULK INSERT | 01_load_staging.sql | sql/01_load_staging.sql | Done | Stub DDL staging SUSEP/Prudential va BULK INSERT |
| 2026-09-15 13:17 | Giai doan 3 | Tao migration khoi tao schema DWH | V1__create_dwh_schema.sql | migrations/V1__create_dwh_schema.sql | Done | DDL Star Schema: Fact_Premium, Fact_Claims, Dim_Customer (SCD2), Dim_Policy, Dim_Date, Dim_Region |
| 2026-09-15 13:17 | Giai doan 4 | Tao script bat CDC va tao bang Watermark | 02_enable_cdc.sql | sql/02_enable_cdc.sql | Done | Bat CDC tren staging DB/table, tao bang ETL_Watermark luu LSN |
| 2026-09-15 13:17 | Giai doan 4 | Tao SP xu ly Dim_Customer theo SCD Type 2 | 03_sp_dim_customer_scd2.sql | sql/03_sp_dim_customer_scd2.sql | Done | DDL ETL_Audit_Log va stub sp_Load_DimCustomer voi MERGE SCD2, TRY...CATCH |
| 2026-09-15 13:17 | Giai doan 4 | Tao SP xu ly cac Dimension con lai | 04_sp_dim_others.sql | sql/04_sp_dim_others.sql | Done | Stubs cho sp_Load_DimPolicy, sp_Load_DimDate, sp_Load_DimRegion kem Audit Log |
| 2026-09-15 13:17 | Giai doan 4 | Tao SP xu ly Fact_Premium | 05_sp_fact_premium.sql | sql/05_sp_fact_premium.sql | Done | Stub sp_Load_FactPremium lookup Dim keys, MERGE UPSERT, Audit Log |
| 2026-09-15 13:17 | Giai doan 4 | Tao SP xu ly Fact_Claims | 06_sp_fact_claims.sql | sql/06_sp_fact_claims.sql | Done | Stub sp_Load_FactClaims lookup Dim keys, MERGE UPSERT, Audit Log |
| 2026-09-15 13:17 | Giai doan 5 | Tao script kiem dinh chat luong du lieu | 07_data_quality_checks.sql | sql/07_data_quality_checks.sql | Done | DDL DQ_Check_Log, procedure sp_Run_DataQualityChecks voi cac rule DQ va ngat pipeline |
| 2026-09-15 13:17 | Giai doan 6 | Tao Airflow DAG dieu phoi pipeline | insurance_dwh_pipeline.py | dags/insurance_dwh_pipeline.py | Done | Dinh nghia cac task load_staging, dim (parallel), fact, DQ, notify, retries=3 |
| 2026-09-15 13:17 | Giai doan 7 | Tao tai lieu README tong quan du an | README.md | README.md | Done | Day du 9 muc bat buoc, mo ta du an, kien truc, cong nghe, khong icon |
| 2026-09-15 13:18 | Giai doan 8 | Tao file giu cho thu muc Power BI | .gitkeep | powerbi/.gitkeep | Done | Thu muc luu dashboard Power BI (.pbix) o Giai doan 8 |
| 2026-09-15 13:18 | Scaffold | Hoan thanh dung suon toan bo repo | Toan bo 17 files | / | Done | Hoan tat scaffold 17 files theo dung 8 giai doan trong implementation-guide.md |
| 2026-09-15 13:20 | Tai lieu | Tao bo tai lieu giai thich du an, thuat ngu, khung data dictionary, huong dan chay, insight va tuning theo tien do thuc te | architecture-explained.md; glossary.md; data-dictionary.md; how-to-run.md; insights.md; performance-tuning-summary.md | docs/architecture-explained.md; docs/glossary.md; docs/data-dictionary.md; docs/how-to-run.md; docs/insights.md; docs/performance-tuning-summary.md | Done | Phan chua co du lieu/ket qua xac minh duoc ghi ro la da len ke hoach, chua trien khai |
| 2026-09-15 13:24 | Review | Duyet tinh toan bo repo, doi chieu tai lieu nguon, sua sai lech cau truc README va Docker Compose | review-report-2026-09-15.md; README.md; docker-compose.yml; how-to-run.md | log/review-report-2026-09-15.md; README.md; docker-compose.yml; docs/how-to-run.md | Done | Khong chay Docker/SQL Server/Airflow; con .cursor/rules/ can nguoi dung xac nhan vi nam ngoai cau truc tai lieu nguon |
| 2026-09-15 13:25 | Review | Hoan tat kiem tra tinh sau sua va loai bo thuoc tinh Docker Compose da loi thoi | review-report-2026-09-15.md; docker-compose.yml | log/review-report-2026-09-15.md; docker-compose.yml | Done | PASS: parse YAML/Compose, cu phap AST DAG, JSON notebook, can bang block comment SQL va kiem tra whitespace |
| 2026-09-15 13:25 | Review | Dong bo huong dan chay voi service Airflow standalone sau khi chuan hoa Docker Compose | how-to-run.md | docs/how-to-run.md | Done | Ghi ro Airflow khoi tao metadata database/tai khoan khi khoi dong; chua chay xac minh container |
| 2026-09-15 13:29 | Tai lieu | Tao tai lieu giai thich cau truc thu muc hien tai va chuc nang tung khu vuc/file | repository-structure.md; README.md | docs/repository-structure.md; README.md | Done | Ghi ro vai tro va trang thai cua tung thu muc/file; phan con la khung duoc danh dau |
| 2026-09-15 15:08 | Tai lieu | Tai cau truc thu muc docs thanh 4 nhom chuyen biet va cap nhat README.md tieng Viet co dau | README.md; docs/README.md; docs/architecture/*; docs/guides/*; docs/reports/*; docs/specs/* | docs/ | Done | Phan chia docs/ thanh architecture, guides, reports, specs kem README.md dieu huong; README.md chuan tieng Viet co dau |
| 2026-09-18 19:30 | Kien truc & ML | Nang cap quy mo du lieu len ~2.5GB (Porto Seguro 1.5M rows) va tich hop Machine Learning Batch Prediction vao DWH & Airflow | ml/*; sql/08_sp_load_risk_predictions.sql; dags/insurance_dwh_pipeline.py; migrations/V1__create_dwh_schema.sql; docs/*; README.md | / | Done | Thay Prudential bang Porto Seguro Safe Driver (~1.5M rows); tao ml/train_risk_model.py, ml/predict_risk_batch.py, sql/08_..., cap nhat DAG va DWH schema |
| 2026-09-18 20:05 | Governance | Task P1-WF-01: Chuan hoa Cursor workflow rules cho personal DWH project | .cursor/rules/*.mdc, .gitignore | .cursor/rules/, .gitignore, log/progress-log.md | Done | Loai bo multi-member template (TV1/2/3, branch tv1/2/3, docs/logs, docs/setup); chot single-project subsystem, canonical log/progress-log.md, canonical docs/guides/how-to-run.md, Git workflow ca nhan, cho phep version-control .cursor/rules/; validation grep sach va git diff --check pass |
| 2026-09-18 20:15 | Governance | Task P1-WF-02: Chuan hoa ngu nghia trang thai tien do va dong bo tai lieu | log/progress-log.md, README.md, docs/specs/implementation-guide.md, docs/architecture/repository-structure.md, docs/guides/how-to-run.md | log/progress-log.md, README.md, docs/ | Done | Dinh nghia bo tu vung trang thai (SCAFFOLD, STATIC_PASS, RUNTIME_PASS, BLOCKED, DONE, FAILED); them Audit Note cho lich su cu; lap bang snapshot 13 subsystems; phan dinh kien truc muc tieu vs hien trang trong README va docs; khong sua code |
| 2026-09-18 20:25 | Governance | Task P1-WF-03: Thiet lap repository validation layer | scripts/validate_repo.py; docs/guides/how-to-run.md; .cursor/rules/03-kiem-tra-git-va-review.mdc; README.md; docs/architecture/repository-structure.md | scripts/; docs/; .cursor/rules/; log/progress-log.md; README.md | Done | Tao scripts/validate_repo.py su dung stdlib + PyYAML kiem tra 44 tieu chi tinh (canonical files, compose, Python AST, notebook JSON, SQL block comment); them Runtime Validation Checklist 11 subsystems vao docs/guides/how-to-run.md; cap nhat quality gate rule; xac nhan khong co runtime claim gia |
| 2026-09-18 21:15 | Governance | Task P1-WF-04: Canonicalize brvehins1 dataset across the repository | README.md; docs/**; scripts/validate_repo.py; notebooks/01-eda.ipynb; log/progress-log.md | / | Done | Chot brvehins1 (5 partitions, 1,965,355 rows, 23 cols) la canonical dataset duy nhat; danh dau susep.gov.br la legacy; gan nhan STALE SCAFFOLD cho code SQL/ML/DAG cu; cap nhat static validator pass 50 checks; loai bo toan bo tham chieu stale (Porto Seguro, Prudential, 8.3M/10M/2.5GB rows/size cu); khong commit git |

## Current Implementation State (Snapshot 2026-09-18)

| STT | Subsystem | Trang thai hien tai | Bang chung thuc te | Dieu kien chuyen trang thai tiep theo |
|---|---|---|---|---|
| 1 | Data/raw (SUSEP, Porto Seguro) | SCAFFOLD | Chi co data/raw/.gitkeep; chua co file CSV tho nao duoc tai ve | Tai file CSV SUSEP (~8.3M rows) va Porto Seguro (~1.5M rows) vao data/raw/ |
| 1a | Data/raw (brvehins1 - Canonical) | STATIC_PASS | 5 partition CSV (`brvehins1a.csv` den `brvehins1e.csv`) hien dien tai `data/raw/brvehins1/` voi tong 1,965,355 dong va 23 cot dong nhat; check_raw_dataset_brvehins1 pass | Thuc hien P1-DATA-01 EDA va thiet lap Source Data Contract chinh thuc |
| 1b | Data/raw (susep.gov.br - Legacy) | LEGACY | File `insurance_dataset.csv` (~8.3M dong, ~751 MB) luu giu lam tai lieu lich su; khong dung cho canonical pipeline | Bao luu nguyen trang, khong su dung |
| 2 | Docker compose | STATIC_PASS | docker-compose.yml da kiem tra parse tinh cu phap hop le; chua khoi chay container | Chay docker-compose up -d tren Docker/WSL2 va xac nhan container sqlserver, airflow healthy |
| 3 | Migrations (DDL V1) | SCAFFOLD | migrations/V1__create_dwh_schema.sql chua DDL stub dang block comment; chua apply qua migration tool | Bo comment DDL, cau hinh cong cu migration (Flyway/DbUp) va thuc thi thanh cong vao SQL Server |
| 4 | Staging load | SCAFFOLD | sql/01_load_staging.sql chua DDL staging va lenh BULK INSERT stub dang block comment | Dinh nghia dung schema cot theo CSV that va chay BULK INSERT thanh cong vao Staging_InsuranceRaw |
| 5 | CDC | SCAFFOLD | sql/02_enable_cdc.sql chua lenh bat sys.sp_cdc_enable_db va bang watermark stub | Chay script tren SQL Server co SQL Server Agent hoat dong; xac nhan CDC capture jobs va bang watermark hoat dong |
| 6 | SCD2 (Customer) | SCAFFOLD | sql/03_sp_dim_customer_scd2.sql chua khung sp_Load_DimCustomer voi MERGE stub dang comment | Hoan thien logic MERGE insert new / expire old va kiem tra tinh dung dan qua du lieu test/that |
| 7 | Fact load (Premium, Claims) | SCAFFOLD | sql/05_sp_fact_premium.sql va sql/06_sp_fact_claims.sql chua khung sp_Load_Fact* voi MERGE stub | Cai dat lookup surrogate key, MERGE UPSERT, kiem tra audit log va tinh idempotent |
| 8 | Data Quality check | SCAFFOLD | sql/07_data_quality_checks.sql chua khung procedure sp_Run_DataQualityChecks voi cac rule stub | Hoan thien cac rule kiem tra (not null, unique, FK integrity), ghi log vao DQ_Check_Log va tra status loi dung |
| 9 | Airflow DAG | STATIC_PASS | dags/insurance_dwh_pipeline.py pass py_compile; task chi la stub EmptyOperator/PythonOperator in log | Ket noi DAG voi SQL Server qua provider/hook va chay thanh cong tren Airflow scheduler/webserver |
| 10 | ML model training | STATIC_PASS | ml/train_risk_model.py pass py_compile; ham trich xuat dac trung va huan luyen dang tra ve stub | Ket noi du lieu that tu Porto Seguro/DWH, huan luyen model that va sinh file artifact ml/risk_model.pkl |
| 11 | ML batch scoring | STATIC_PASS / SCAFFOLD | ml/predict_risk_batch.py pass py_compile; sql/08_sp_load_risk_predictions.sql chua MERGE stub | Chay batch scoring voi du lieu that va nap ket qua vao Fact_Customer_Risk_Prediction qua sp_Load_CustomerRiskPredictions |
| 12 | Performance tuning | SCAFFOLD | docs/reports/performance-tuning-summary.md dang la template ke hoach cho Giai doan 7; chua co script index/partitioning | Tao baseline query, do STATISTICS IO/TIME, tao index/partitioning va do lai ket qua so sanh before/after |
| 13 | Power BI dashboard | SCAFFOLD | Chi co powerbi/.gitkeep; chua co file .pbix | Xay dung model, visual bao cao va luu file powerbi/insurance-dashboard.pbix o Giai doan 8 |
| 3 | Migrations (DDL V1) | STALE SCAFFOLD | `migrations/V1__create_dwh_schema.sql` chua DDL stub theo mo hinh SUSEP/Porto Seguro cu; chua refactor theo brvehins1 | Refactor DDL migration tao schema xe co gioi (Driver Profile, Vehicle, Geography, Policy Risk Fact) |
| 4 | Staging load | STALE SCAFFOLD | `sql/01_load_staging.sql` chua DDL staging cu; chua refactor theo 23 cot brvehins1 | Refactor DDL staging va BULK INSERT cho 5 partition CSV brvehins1 |
| 5 | CDC / Batch Watermark | STALE SCAFFOLD | `sql/02_enable_cdc.sql` chua khung CDC / watermark theo mo hinh cu | Refactor co che watermark / incremental cho cac partition brvehins1 |
| 6 | SCD2 (Customer) | STALE SCAFFOLD | `sql/03_sp_dim_customer_scd2.sql` tao theo Dim_Customer cu (brvehins1 khong co CustomerId/SCD2) | Thay the bang stored procedure nap Dim_Driver_Profile va Dim_Vehicle |
| 7 | Fact load (Policy Risk) | STALE SCAFFOLD | `sql/05_sp_fact_premium.sql` va `sql/06_sp_fact_claims.sql` tao theo Fact tach roi cu | Refactor thanh `sp_Load_FactPolicyRisk` ket hop exposure, premium, claim counts & amounts |
| 8 | Data Quality check | STALE SCAFFOLD | `sql/07_data_quality_checks.sql` tao theo rule cu | Refactor rule kiem dinh chat luong tren 23 cot cua brvehins1 |
| 9 | Airflow DAG | STATIC_PASS / STALE SCAFFOLD | `dags/insurance_dwh_pipeline.py` pass py_compile nhung task phan anh pipeline cu | Refactor graph dependency va task logic theo pipeline brvehins1 |
| 10 | ML model training | STATIC_PASS / STALE SCAFFOLD | `ml/train_risk_model.py` pass py_compile nhung ham trich xuat dac trung theo Porto Seguro cu | Refactor feature extraction va train model du doan rui ro ton that tren du lieu brvehins1 |
| 11 | ML batch scoring | STATIC_PASS / STALE SCAFFOLD | `ml/predict_risk_batch.py` va `sql/08_sp_load_risk_predictions.sql` phan anh schema cu | Refactor scoring module va procedure nap vao `Fact_Vehicle_Risk_Prediction` |
| 12 | Performance tuning | SCAFFOLD | `docs/reports/performance-tuning-summary.md` dang la template ke hoach cho Giai doan 7 | Tao baseline query tren Fact ~1.965M dong, do STATISTICS IO/TIME, tao index/partitioning va bao cao |
| 13 | Power BI dashboard | SCAFFOLD | Chi co powerbi/.gitkeep; chua co file .pbix | Xay dung data model va visual phan tich ton that / du doan rui ro o Giai doan 8 |

## Giai doan hien tai
Giai doan 1 — Khao sat & chuan bi du lieu that (Governance & Validation Layer)
Giai doan 1 — Khao sat & chuan bi du lieu that
Giai doan 1 — Khao sat & chuan bi du lieu that (Dataset Canonical: brvehins1)

## Viec tiep theo can lam
P1-WF-03 — Add repository validation layer.
1. Hoan thanh Giai doan 1 trong docs/specs/implementation-guide.md: tai 2 bo du lieu SUSEP (~8.3M dong) va Porto Seguro (~1.5M dong) ve data/raw/.
2. Chay khao sat EDA trong notebooks/01-eda.ipynb: kiem tra shape, dtypes, null check, duplicate check tren du lieu that.
3. Dien thong tin du lieu that vao docs/architecture/data-dictionary.md va tong hop danh sach van de chat luong du lieu can xu ly.
P1-DATA-01 — Real EDA & Source Data Contract:
1. Chay phan tich EDA thuc te trong `notebooks/01-eda.ipynb` (hoac script) tren 5 partition `data/raw/brvehins1/` (phan bo exposure, loss ratio, tan suat claim zero-inflation).
2. Thiet lap Source Data Contract chinh thuc cho `brvehins1` (schema, types, constraints, business domain assumptions).
3. Len ke hoach refactor staging, migration DDL, SQL stored procedures, ML modules, va Airflow DAG theo data contract moi.
