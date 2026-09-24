# Chạy Track A SUSEP như thế nào?

## Điều kiện trước khi chạy là gì?

- Docker SQL Server đang chạy: `docker compose up -d sqlserver`.
- `.env` local có `SQLSERVER_SA_PASSWORD`; file này bị ignore và không được commit.
- Dùng **đúng virtual environment của repo**. Nó pin `scikit-learn==1.7.2` cho Track B artifact; global Python đang có version khác nên không dùng để thao tác ML artifact.
- Không chỉnh `data/raw/susep.gov.br/insurance_dataset.csv`.

## Thứ tự chạy an toàn

```powershell
# 1. Apply migrations theo version bằng sqlcmd trong container.
Get-Content -Raw migrations\V11__create_susep_staging.sql | docker compose exec -T sqlserver /bin/bash -lc '/opt/mssql-tools18/bin/sqlcmd -C -S localhost -U sa -P "$MSSQL_SA_PASSWORD" -b -r1'
Get-Content -Raw migrations\V12__create_susep_market_dwh.sql | docker compose exec -T sqlserver /bin/bash -lc '/opt/mssql-tools18/bin/sqlcmd -C -S localhost -U sa -P "$MSSQL_SA_PASSWORD" -b -r1'
Get-Content -Raw migrations\V13__create_susep_quality_gate.sql | docker compose exec -T sqlserver /bin/bash -lc '/opt/mssql-tools18/bin/sqlcmd -C -S localhost -U sa -P "$MSSQL_SA_PASSWORD" -b -r1'

# 2. Nạp raw immutable vào staging. Export secret từ .env bằng cách phù hợp với shell local.
.\.venv\Scripts\python.exe scripts\load_susep_to_staging.py --batch-size 20000

# 3. Tạo dimensions và one-row-per-stage fact.
Get-Content -Raw sql\09_load_susep_market_dwh.sql | docker compose exec -T sqlserver /bin/bash -lc '/opt/mssql-tools18/bin/sqlcmd -C -S localhost -U sa -P "$MSSQL_SA_PASSWORD" -b -r1'

# 4. Đối soát trực tiếp bằng cách đọc lại raw, sau đó chạy DQ.
.\.venv\Scripts\python.exe scripts\reconcile_susep_source_to_fact.py
Get-Content -Raw sql\10_run_susep_quality_gate.sql | docker compose exec -T sqlserver /bin/bash -lc '/opt/mssql-tools18/bin/sqlcmd -C -S localhost -U sa -P "$MSSQL_SA_PASSWORD" -b -r1'
```

## Rerun nghĩa là gì?

Chạy lại loader với cùng file SHA-256 phải trả `SKIPPED`. Nó không thêm stage row nhờ application lock, successful source-version lookup và unique technical identity. Running `sql/09...` lần hai cũng không tạo fact mới vì fact unique theo `SusepStageRowId`.

## Làm sao đọc kết quả DQ?

`HARD / PASS` là điều kiện được phép downstream. `WARNING` là fact về source cần thấy trong báo cáo, không phải lỗi để pipeline tự xóa data. Ví dụ premium/claims âm của SUSEP là warning; cho chúng thành `>= 0` hard rule là làm sai contract.

## Nếu cần test failure an toàn?

```sql
EXEC dq.sp_RunSusepQualityGate
    @RunLabel=N'controlled-invalid-test',
    @InjectControlledFailure=1;
```

Lệnh phải throw và ghi log fail, nhưng không insert/update/delete raw, staging hay fact. Sau đó chạy lại production gate để xác nhận data canonical vẫn pass.
