# P1-INGEST-01 — Tạo staging schema thực

Ngày: 2026-09-22

Kết quả: PASS

## Mục tiêu

Tạo staging schema SQL Server phản ánh đúng frozen contract `brvehins1`, đồng thời thêm metadata lineage kỹ thuật mà không tạo business identifier giả.

## File đã thay đổi

- `migrations/V2__create_staging_schema.sql`
- `sql/01_load_staging.sql`
- `docs/architecture/staging-design.md`
- `reports/checkpoints/P1-INGEST-01.md`
- `log/progress-log.md`

## Lệnh đã chạy

```text
sqlcmd < migrations/V2__create_staging_schema.sql
sqlcmd < sql/01_load_staging.sql
sqlcmd < staging source-column contract assertion
sqlcmd < transactional staging loadability smoke test
sqlcmd < migrations/V2__create_staging_schema.sql   # rerun
python scripts/validate_repo.py
git diff --check
docker compose ps
```

## Bằng chứng và quyết định

- `stg.BrVehIns1` và `stg.BrVehIns1Landing` tồn tại trong `DWH_Insurance`.
- Assertion runtime xác minh đúng 23 source columns, type, precision/scale và nullable policy: `STAGING_CONTRACT_PASS | 23`.
- `stg.BrVehIns1` có 29 cột: 23 source columns và 6 cột kỹ thuật (`StageRowId`, `BatchId`, `SourceFile`, `SourceRowNumber`, `SourceRecordHash`, `LoadTimestampUtc`).
- `SourceFile + SourceRowNumber` có unique index kỹ thuật; `(BatchId, SourceFile)` có foreign key về `meta.IngestionBatch`, bảo toàn lineage batch.
- Landing dùng text để loader có thể phát hiện numeric parse error theo contract trước khi typed staging nhận row. Typed staging dùng `SMALLINT`, `INT`, `DECIMAL(19,6)` và `NVARCHAR` theo data dictionary.
- Smoke test tạo một batch/row hợp lệ trong transaction, đọc được `TransactionalSmokeRows = 1`, rollback và xác nhận `PersistentStagingRows = 0`.
- Lần smoke đầu bị SQL Server từ chối vì session `sqlcmd` thiếu `QUOTED_IDENTIFIER` cho filtered idempotency index. `sql/01_load_staging.sql` đã được bổ sung đầy đủ required `SET` options; retry thành công. Đây là lỗi session setup, không có raw/staging row nào được persist.
- V2 rerun thành công; `meta.SchemaVersion` có `V1`, `V2` một lần mỗi version.
- Static validator: `41 PASSED | 0 FAILED | 8 SKIPPED`; `git diff --check` pass; SQL Server container vẫn `Up`.

## Tiêu chí PASS

- [x] Staging table tồn tại trong SQL Server.
- [x] 23 source columns khớp frozen data contract.
- [x] SQL type, nullability, precision và scale đã được assertion runtime.
- [x] Metadata ingestion và technical identity được document.
- [x] Typed staging đã loadable bằng smoke test rollback an toàn.
- [x] Không có `CustomerId`, `PolicyNumber`, fake SCD2 hay raw mutation.

## Bước tiếp theo chính xác

`P1-INGEST-02` — triển khai một loader duy nhất cho `brvehins1a.csv`, chứng minh source-to-staging reconciliation và rerun cùng partition không tạo duplicate.
