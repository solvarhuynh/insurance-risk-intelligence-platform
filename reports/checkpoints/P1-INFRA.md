# P1-INFRA-01 / P1-INFRA-02 — SQL Server infrastructure và bootstrap

Ngày: 2026-09-22

Kết quả: PASS

## Mục tiêu

Thiết lập foundation runtime thật cho `DWH_Insurance`: SQL Server chạy bằng Docker, credential lấy từ environment, và bootstrap metadata có thể chạy lại an toàn theo canonical source contract `brvehins1`.

## File đã thay đổi

- `.env.example`
- `docker-compose.yml`
- `migrations/V1__create_dwh_schema.sql`
- `README.md`
- `docs/guides/how-to-run.md`
- `reports/checkpoints/P1-INFRA.md`
- `log/progress-log.md`

Tệp `.env` local đã được tạo theo convention hiện có nhưng bị Git ignore; không ghi hay xuất secret vào report/log.

## Lệnh đã chạy

```text
docker version --format '{{.Server.Version}}'
docker compose config -q
docker compose ps
docker exec insurance_sqlserver ... sqlcmd ...
sqlcmd < migrations/V1__create_dwh_schema.sql
sqlcmd < migrations/V1__create_dwh_schema.sql   # rerun idempotency
python scripts/validate_repo.py
git diff --check
git check-ignore -v -- .env
```

## Bằng chứng runtime

- Docker Engine Server version `29.6.1` phản hồi; `docker compose config -q` thành công.
- Container `insurance_sqlserver` đang `Up`, publish cổng `1433`.
- `sqlcmd` chạy thành công trong container bằng `MSSQL_SA_PASSWORD` của môi trường container; secret không được in ra.
- Database `DWH_Insurance` tồn tại.
- Schemas tồn tại: `meta`, `stg`, `dwh`, `dq`.
- Metadata tables tồn tại đúng scope foundation: `meta.SchemaVersion`, `meta.SourceFileManifest`, `meta.IngestionBatch`, `meta.PipelineAudit`.
- `meta.SchemaVersion` có `V1`.
- Manifest có đúng năm partition `brvehins1[a-e].csv`, mỗi partition expected `393071` dòng.
- Kiểm kê `Dim_Customer`, `Dim_Policy`, `Fact_Premium`, `Fact_Claims`, `Fact_Customer_Risk_Prediction` trả về `0` object.
- Bootstrap migration chạy lại thành công và không tạo bản ghi version/manifest trùng.
- `.env` được ignore bởi rule `.gitignore:7:*.env`.
- Static validator: `40 PASSED | 0 FAILED | 8 SKIPPED`; `git diff --check` exit code `0`.

## Quyết định

- SQL Server là service runtime duy nhất của stage này. Airflow nằm trong profile `orchestration`, chưa khởi chạy và không được suy diễn là runtime pass.
- `MSSQL_SA_PASSWORD` dùng environment variable; `.env.example` chỉ là template không secret.
- V1 chỉ tạo foundation database metadata/audit. Không tạo staging business table, dimension, fact, SCD2 hay CDC ở stage này.
- `SourceFileManifest` là manifest canonical để stage ingest đối soát row count; `IngestionBatch` có unique filtered index cho một batch `SUCCESS` trên mỗi source file.

## Tiêu chí PASS

- [x] SQL Server Docker container đang chạy.
- [x] SQL Server chấp nhận kết nối thật.
- [x] `DWH_Insurance` tồn tại.
- [x] Foundational schemas và metadata tables tồn tại.
- [x] Bootstrap có thể chạy lại an toàn.
- [x] Không có kiến trúc Customer/Policy legacy được đưa trở lại.
- [x] Credential không nằm trong Git-tracked configuration.

## Bước tiếp theo chính xác

`P1-INGEST-01` — tạo `stg` schema và staging table phản ánh đúng 23 cột canonical cùng metadata ingestion đã freeze trong source contract.
