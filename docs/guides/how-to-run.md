# Cách chạy và xác thực nền tảng

## Điều kiện hiện tại

Nguồn chuẩn `brvehins1` đã có trong `data/raw/brvehins1/`. File `data/raw/susep.gov.br/insurance_dataset.csv` là **LEGACY / NON-CANONICAL** và không chạy cùng pipeline chuẩn.

Raw là chỉ-đọc theo quy ước dự án. Không tạo output, file staging hoặc prediction trong `data/raw/`.

## Kiểm tra tĩnh

Chạy từ root repository:

```powershell
python scripts/validate_repo.py
python -m py_compile scripts/validate_repo.py ml/train_risk_model.py ml/predict_risk_batch.py dags/insurance_dwh_pipeline.py
docker compose config
git diff --check
```

Kết quả thành công ở đây là `STATIC_PASS`, không phải `RUNTIME_PASS`.

## Python dependencies

Host runtime và tooling được tách thành hai manifest. Không chạy `pip install apache-airflow` trên host: Airflow chỉ thuộc image Docker profile `orchestration`.

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
.\.venv\Scripts\python -c "import numpy, pandas, pyodbc, yaml, jupyterlab; print('dependency imports OK')"
```

Staging loader cần Microsoft ODBC Driver 18 for SQL Server trên host ngoài package `pyodbc`. Xem lý do từng dependency tại [python-dependencies.md](../architecture/python-dependencies.md).

## Trình tự runtime được phép

1. `P1-DATA-01` đã profile dữ liệu và lưu bằng chứng tại `reports/data/`.
2. `P1-DATA-02` đã đóng băng contract, grain, technical key và policy DQ tại `docs/architecture/source-data-contract.md`.
3. Thiết lập SQL Server qua Docker, xác minh kết nối và bootstrap `DWH_Insurance`.
4. Nạp một partition, đối soát và kiểm tra idempotency trước khi nạp cả năm partition.
5. Tạo dimensions, fact và quality gate dựa trên contract đã đóng băng.

## SQL Server foundation đã xác minh

1. Tạo `.env` local từ `.env.example` và đặt `SQLSERVER_SA_PASSWORD` là một mật khẩu cục bộ riêng, thỏa điều kiện phức tạp của SQL Server. Không commit `.env`.

2. Parse và khởi động riêng SQL Server:

```powershell
docker compose config -q
docker compose up -d sqlserver
docker compose ps
```

3. Kiểm tra kết nối mà không in password ra terminal:

```powershell
docker compose exec -T sqlserver /bin/bash -lc '/opt/mssql-tools18/bin/sqlcmd -C -S localhost -U sa -P "$MSSQL_SA_PASSWORD" -b -W -Q "SELECT 1 AS ConnectionOK"'
```

4. Chạy hoặc chạy lại bootstrap idempotent:

```powershell
Get-Content -Raw migrations/V1__create_dwh_schema.sql | docker compose exec -T sqlserver /bin/bash -lc '/opt/mssql-tools18/bin/sqlcmd -C -S localhost -U sa -P "$MSSQL_SA_PASSWORD" -b -r1'
```

Lệnh bootstrap đã được chạy hai lần thành công. Nó tạo `DWH_Insurance`, schemas `meta`, `stg`, `dwh`, `dq`, `SourceFileManifest`, `IngestionBatch`, `PipelineAudit` và `SchemaVersion`; chưa tạo business fact/dimension giả.

Airflow thuộc profile `orchestration` và không phải phần runtime đã chứng minh trong foundation hiện tại. Không chạy SQL, ML hoặc Airflow scaffold cũ như một pipeline thực.

## Staging runtime đã xác minh

Sau khi chạy migrations V1–V5 và đã set `SQLSERVER_SA_PASSWORD` trong process environment, nạp một partition bằng parser streaming:

```powershell
python scripts/load_brvehins1_to_staging.py --source-file brvehins1a.csv --batch-size 5000
```

Lặp cùng command cho `brvehins1b.csv` đến `brvehins1e.csv`. Rerun một partition SUCCESS trả `SKIPPED`, không thêm row. SQL entry point `sql/01_load_staging.sql` chỉ kiểm tra batch status; nó không thay thế Python loader vì source CSV có quoted comma và cần ordinal file chính xác.

Sau khi staging năm partition đã đối soát, chạy V6 rồi entry point nạp dimension:

```powershell
Get-Content -Raw migrations/V6__create_canonical_dimensions.sql | docker compose exec -T sqlserver /bin/bash -lc '/opt/mssql-tools18/bin/sqlcmd -C -S localhost -U sa -P "$MSSQL_SA_PASSWORD" -b -r1'
Get-Content -Raw sql/04_load_canonical_dimensions.sql | docker compose exec -T sqlserver /bin/bash -lc '/opt/mssql-tools18/bin/sqlcmd -C -S localhost -U sa -P "$MSSQL_SA_PASSWORD" -b -r1'
```

Lệnh thứ hai có thể chạy lại an toàn: dimension tuple đã có sẽ không được thêm lần nữa. Không chạy `sql/03_sp_dim_customer_scd2.sql` hoặc `sql/04_sp_dim_others.sql`; đó là scaffold lịch sử không thuộc canonical model.

## Ý nghĩa trạng thái

- `SCAFFOLD`: chỉ mới có khung hoặc template.
- `STATIC_PASS`: đã qua kiểm tra cú pháp, parse hoặc kiểm tra file tĩnh.
- `RUNTIME_PASS`: đã chạy thành công với bằng chứng thực tế.
- `BLOCKED`: thiếu điều kiện tiên quyết.
- `FAILED`: kiểm tra hoặc runtime thất bại.
- `DONE`: toàn bộ Definition of Done của task đã hoàn tất.
