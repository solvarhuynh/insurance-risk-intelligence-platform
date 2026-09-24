# Chạy và kiểm tra Insurance Data Platform

## Quy tắc an toàn trước khi chạy

- Chạy từ repository root và dùng `.\.venv\Scripts\python.exe` cho host ML/artifact.
- Tạo `.env` từ `.env.example`, đặt `SQLSERVER_SA_PASSWORD`, không commit file này.
- Không sửa bất kỳ file `data/raw/**` nào. Raw là input immutable/read-only.
- Không retrain Track B chỉ để demo; artifact/scoring hiện hành đã có contract và runtime evidence.
- Không join SUSEP với brvehins1/Prudential trong SQL, BI hay code.

## 1. Static validation

```powershell
.\.venv\Scripts\python.exe scripts\validate_repo.py
$pythonFiles = @(Get-ChildItem scripts -Filter *.py -File | ForEach-Object FullName) + @(Get-ChildItem ml -Filter *.py -File | ForEach-Object FullName) + @((Resolve-Path dags\insurance_dwh_pipeline.py))
& .\.venv\Scripts\python.exe -m py_compile $pythonFiles
docker compose --profile orchestration config
git diff --check
```

Static validation kiểm tra file/header/syntax/SQL structure. Nó không thay thế runtime SQL, DQ, Airflow hay Power BI refresh.

## 2. Khởi động runtime

```powershell
docker compose --profile orchestration up -d --build
docker compose --profile orchestration ps
```

SQL Server chạy service `sqlserver`; Airflow chạy profile `orchestration`. Raw mount vào SQL/Airflow read-only. Không xóa Docker volume để “chạy lại sạch” trên instance đang chứa evidence.

## 3. Track A — SUSEP

Source: `data/raw/susep.gov.br/insurance_dataset.csv`.

Để chạy loader/reconciliation từ Airflow container (giữ đúng environment credential/mount):

```powershell
docker compose exec -T airflow python /opt/airflow/project/scripts/load_susep_to_staging.py --source-path /opt/airflow/raw_data/susep.gov.br/insurance_dataset.csv --server sqlserver,1433
docker compose exec -T airflow python /opt/airflow/project/scripts/reconcile_susep_source_to_fact.py --source-path /opt/airflow/raw_data/susep.gov.br/insurance_dataset.csv --server sqlserver,1433
```

First successful source version là batch `0EDEB285-DB67-4159-A6D5-FE85F00F085A`; rerun phải in `SKIPPED`, không duplicate. DWH load entry point là `sql/09_load_susep_market_dwh.sql`; production DQ entry point là `sql/10_run_susep_quality_gate.sql`. Xem `docs/susep/how-to-run-track-a.md` và `P1-SUSEP-02/04/05.md` trước khi chạy full workload.

Expected reconciliation:

```text
source = staging = fact = 8,338,214 rows
premium source = staging = fact
claims source = staging = fact
```

## 4. Track B — brvehins1 / ML

Track B đã có `stg.BrVehIns1 = FactRiskObservation = 1,965,355`. Production DQ/chấm điểm được Airflow gọi trong DAG; không cần full reload hoặc training lại để smoke check.

Artifact reload tối thiểu:

```powershell
.\.venv\Scripts\python.exe -c "import joblib; print(type(joblib.load('ml/artifacts/claim_risk_model_v001.joblib')).__name__)"
```

Prediction expectation: `bounded_held_out_test = 20,000`, duplicate technical identity = 0. Artifact là cross-sectional `HasClaim` association, không future customer/policy probability.

## 5. Airflow valid run và status

```powershell
docker compose exec -T airflow airflow dags list-import-errors --output plain
docker compose exec -T airflow airflow dags trigger insurance_data_platform --run-id <UUID>
docker compose exec -T airflow airflow tasks states-for-dag-run insurance_data_platform <UUID>
```

Valid evidence: run `44294f58-1808-4cd8-8a22-2c90687bf321`, 12/12 tasks `success`. DAG chạy hai route độc lập; task arrows không là cross-track join.

Controlled failure chỉ dùng trong môi trường test:

```powershell
docker compose exec -T airflow airflow dags trigger insurance_data_platform --run-id <UUID> --conf '{"controlled_track_a_dq_failure":true}'
```

Expected: Track-A DQ `failed`, Track-A consumer `upstream_failed`, Track-B consumer `success`. Chi tiết evidence và retry: `reports/checkpoints/P1-ORCH-02.md`.

## 6. Performance và Power BI

Performance evidence có trong `reports/performance-report.md`: Q1/Q2 logical reads giảm khoảng 98,8–98,9% với hai index retained. Đừng kết luận nhanh/chậm chỉ từ một elapsed time cache-hit.

Power BI semantic design: `docs/bi/semantic-model.md`; manual build: `powerbi/README.md`. Hiện không có artifact `.pbix` thật hoặc refresh evidence vì thiếu Power BI Desktop/PBIP toolchain. Status là `BLOCKED_MANUAL`.

## 7. Khi có lỗi

1. Source/path/header: đọc error của loader, sửa mount/path/file contract; không sửa raw.
2. SQL: kiểm tra `docker compose --profile orchestration ps`, credentials và `sqlserver,1433`.
3. DQ: xem `dq.SusepQualityCheckLog` hoặc Track-B quality log; sửa upstream cause rồi rerun maintained task.
4. ML: xác nhận `.venv` scikit-learn 1.7.2 và artifact metadata.
5. Airflow: xem exact task state/log; không chạy consumer nếu prerequisite bị `upstream_failed`.

Các test path/header/SQL unavailable và safe recovery đã được ghi tại `P1-E2E-02.md`.
