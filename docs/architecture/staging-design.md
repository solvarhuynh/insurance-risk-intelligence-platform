# Thiết kế staging canonical — brvehins1

Trạng thái: `RUNTIME_PASS` cho cấu trúc table và cả năm partition sau `P1-INGEST-03`; staging chứa 1,965,355 source rows có đối soát.

## Mục đích

`stg` là lớp SQL giữ bản ghi nguồn `brvehins1` đã parse đúng kiểu dữ liệu để đối soát và làm đầu vào cho DWH. Nó không làm sạch, tổng hợp hoặc suy diễn customer, policy hay claim event.

## Bảng chính

`stg.BrVehIns1` giữ một source row cho mỗi `SourceFile + SourceRowNumber`. Bảng có toàn bộ 23 field canonical theo mapping trong `data-dictionary.md`:

- descriptor: `Gender`, `DrivAge`, `VehYear`, `VehModel`, `VehGroup`, `Area`, `State`, `StateAb`;
- measure: `ExposTotal`, `ExposFireRob`, `PremTotal`, `PremFireRob`, `SumInsAvg`, năm `ClaimNb*` và năm `ClaimAmount*`.

Các measure bắt buộc là `NOT NULL`; descriptor nullable được preserve là `NULL`. Kiểu SQL trùng contract: `SMALLINT` cho `VehYear`, `INT` cho các claim count, `DECIMAL(21,17)` cho `ExposTotal`, `DECIMAL(34,27)` cho `PremTotal`, `DECIMAL(19,6)` cho các decimal measure còn lại và `NVARCHAR` đúng kích thước đã freeze cho text. Hai precision cao hơn được xác minh bằng raw lexical scan, nên không làm tròn float artifact của source.

## Lineage và metadata

- `BatchId`: định danh kỹ thuật của lần ingest partition, foreign key tới `meta.IngestionBatch`.
- `SourceFile`: đúng tên partition canonical; được ràng buộc cùng `BatchId` tới manifest/batch metadata.
- `SourceRowNumber`: ordinal 1-based trong file, không tính header. Unique với `SourceFile`; không phải business key.
- `SourceRecordHash`: SHA-256 fingerprint của serialization logic các field nguồn. Nó phục vụ audit, không được unique vì EDA đã quan sát 14 logical duplicate rows.
- `LoadTimestampUtc`: thời điểm row được đưa vào typed staging.

Không có `CustomerId`, `PolicyNumber`, SCD2 field hoặc identifier nghiệp vụ được tạo ra.

## Loader streaming

`scripts/load_brvehins1_to_staging.py` đọc từng partition bằng Python `csv.DictReader`, nên trường `VehModel` có dấu phẩy nằm trong quote được parse theo CSV đúng chuẩn. Script gán `SourceRowNumber` trực tiếp từ ordinal 1-based của parser, validate 23 field theo contract, tính `SourceRecordHash`, rồi insert theo batch vào `stg.BrVehIns1` qua ODBC Driver 18.

Lựa chọn này thay thế thử nghiệm `BULK INSERT FORMAT=CSV` chỉ ở Linux: provider của SQL Server không nạp được CSV vào bảng có identity metadata cần cho lineage. Không tạo file trung gian, không sửa raw và không suy diễn row ordinal từ physical order của database.

## Idempotency dự kiến

Một partition chỉ có thể có một `meta.IngestionBatch` ở trạng thái `SUCCESS` nhờ filtered unique index của V1. Loader trả về batch thành công hiện có và ghi audit `SKIPPED` nếu nhận cùng `SourceFile`, thay vì thêm staging rows.

## Deployment

Chạy migrations V1–V4, cài `pyodbc` với `pip install -r requirements.txt`, export `SQLSERVER_SA_PASSWORD` và gọi script loader. `sql/01_load_staging.sql` là entry point SQL để xem trạng thái batch sau khi chạy loader.
