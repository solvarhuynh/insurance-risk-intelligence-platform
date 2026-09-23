# P1-INGEST-02 — Nạp và đối soát một partition thật

Ngày: 2026-09-22

Kết quả: PASS

## Mục tiêu

Chứng minh đường nạp canonical bằng riêng `brvehins1a.csv`, đối soát source-to-staging và chứng minh rerun không tạo duplicate.

## File đã thay đổi

- `migrations/V2__create_staging_schema.sql`
- `migrations/V3__create_staging_loader.sql`
- `migrations/V4__remove_unsupported_bulk_landing.sql`
- `migrations/V5__preserve_observed_decimal_precision.sql`
- `sql/01_load_staging.sql`
- `scripts/load_brvehins1_to_staging.py`
- `scripts/profile_brvehins1_numeric_precision.py`
- `requirements.txt`
- `docs/architecture/data-dictionary.md`
- `docs/architecture/source-data-contract.md`
- `docs/architecture/staging-design.md`
- `reports/data/brvehins1-numeric-precision.json`
- `reports/data/brvehins1-eda-summary.md`
- `reports/checkpoints/P1-INGEST-02.md`
- `log/progress-log.md`

## Lệnh đã chạy

```text
python -m pip install -r requirements.txt
python scripts/profile_brvehins1_numeric_precision.py
sqlcmd < migrations/V4__remove_unsupported_bulk_landing.sql
sqlcmd < migrations/V5__preserve_observed_decimal_precision.sql
python scripts/load_brvehins1_to_staging.py --source-file brvehins1a.csv --batch-size 5000
python scripts/load_brvehins1_to_staging.py --source-file brvehins1a.csv --batch-size 5000  # rerun
sqlcmd < source/staging reconciliation assertion
sqlcmd < sql/01_load_staging.sql
python scripts/validate_repo.py
git diff --check
```

## Bằng chứng runtime

- `brvehins1a.csv` có `393,072` dòng vật lý qua `wc -l`: 1 header + **393,071** source rows.
- SUCCESS batch: `56D062D8-5048-4086-A6A0-0F26E17FD6B3`.
- `meta.IngestionBatch`: expected `393,071`, staging `393,071`, rejected `0`, status `SUCCESS`, elapsed `50,047 ms`.
- Assertion trả về `ExpectedSourceRows=393071`, `StagingRows=393071`, `DistinctTechnicalIdentities=393071`.
- Rerun cùng command trả `SKIPPED`, trả về batch SUCCESS có sẵn và tạo audit `SKIPPED`; staging row count không tăng.
- `SourceFile + SourceRowNumber` được gán bởi `csv.DictReader` theo ordinal 1-based của file, không suy diễn từ physical row order SQL Server.
- Source có quoted comma trong `VehModel`; Python CSV parser xử lý đúng RFC CSV trước khi insert parameterized qua ODBC Driver 18.

## Điều chỉnh có bằng chứng

Lần nạp đầu tiên phát hiện `ExposTotal` source row 35 là `0.00547945220023394`, không vừa mapping `DECIMAL(19,6)`. Scanner lexical streaming sau đó đọc đủ 1,965,355 dòng và xác nhận `ExposTotal` cần `DECIMAL(21,17)`, `PremTotal` cần `DECIMAL(34,27)`. V5 cập nhật table rỗng trước khi nạp; không làm tròn hoặc cap raw value.

Server-side `BULK INSERT FORMAT=CSV` trên SQL Server Linux đã được thử và audit đúng là `FAILED`: `CODEPAGE` không được hỗ trợ trên Linux, và provider `BULK` không hỗ trợ CSV khi destination có internal identity cần cho technical ordinal. V4 chỉ xóa landing table/procedure rỗng sau khi xác nhận zero rows; client loader thay thế bằng parser có source ordinal rõ ràng. Các batch FAILED được giữ nguyên trong audit, tất cả có `StagingRows=NULL`, và không có raw/staging data bị persist từ các attempt thất bại.

## Tiêu chí PASS

- [x] `brvehins1a.csv` được nạp qua một loader canonical.
- [x] Source rows = reconciled staging rows = `393,071`.
- [x] Rejected/error rows của SUCCESS batch = `0`.
- [x] Batch metadata có source count, staging count, elapsed time và status.
- [x] Rerun cùng partition là no-op có audit `SKIPPED`, không duplicate.
- [x] Raw CSV không bị sửa.
- [x] Static validator: `46 PASSED | 0 FAILED | 8 SKIPPED`; `git diff --check` pass.

## Bước tiếp theo chính xác

`P1-INGEST-03` — dùng chính `scripts/load_brvehins1_to_staging.py` để nạp B, C, D, E; đối soát cả năm partition, total staging `1,965,355` và thử rerun một partition đã SUCCESS.
