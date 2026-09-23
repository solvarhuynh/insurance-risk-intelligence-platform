# Kiến trúc hiện hành của nền tảng dữ liệu

## Mục tiêu

Dự án xây dựng Motor Insurance Data Warehouse cho dữ liệu `brvehins1`. Nền tảng phục vụ phân tích premium, exposure, giá trị bảo hiểm và claim theo đặc tính người lái, xe và địa lý. Đây là nền tảng dữ liệu trước khi mở rộng sang orchestration, ML, tối ưu hiệu năng và Power BI.

## Nguồn chuẩn và ranh giới dữ liệu

`data/raw/brvehins1/` chứa đúng năm file CSV chuẩn. Raw không được thay đổi, chuẩn hóa hay ghi đầu ra vào lại. File `data/raw/susep.gov.br/insurance_dataset.csv` được phân loại **LEGACY / NON-CANONICAL** và nằm ngoài mọi bước ingest, DWH và DQ hiện hành.

## Luồng đích

```text
Raw brvehins1
  -> import tạm theo partition
  -> staging có BatchId, SourceFile, SourceRowNumber và SourceRecordHash
  -> dimensions được suy ra từ các nhóm thuộc tính thực có trong nguồn
  -> fact ở đúng grain của một bản ghi nguồn
  -> data-quality gate và đối soát raw -> staging -> fact
```

Mỗi batch phải được ghi metadata, đối soát số dòng và có hành vi idempotent khi chạy lại cùng file. Khóa nhận diện nguồn là kỹ thuật; nó không được trình bày như một mã nghiệp vụ của khách hàng hoặc hợp đồng.

## Quyết định đã đóng băng sau EDA

- Grain là một source-delivered aggregate risk observation, không phải policy/customer/event cá thể.
- Technical identity là `SourceFile + SourceRowNumber`; 14 dòng logic trùng vẫn được preserve.
- Nullable, duplicate, invalid-value và partition semantics được quy định tại `source-data-contract.md`.
- Các metric dẫn xuất xử lý mẫu số bằng 0 bằng `NULL`, không infinity.
- Không có SCD2 thật nếu nguồn không có lịch sử thay đổi của một business entity.

## Trạng thái mã hiện có

| Khu vực | Trạng thái | Cách xử lý |
|---|---|---|
| `migrations/V1__create_dwh_schema.sql` | RUNTIME_PASS | Bootstrap idempotent đã tạo database, schemas `meta/stg/dwh/dq`, manifest và audit metadata. |
| `sql/` và migration business kế tiếp | STALE SCAFFOLD — REQUIRES REFACTOR | Thay bằng staging, DWH và DQ dựa trên source contract. |
| `ml/` và `dags/` | STALE SCAFFOLD — REQUIRES REFACTOR | Không dùng làm bằng chứng runtime; hoãn đến sau DQ. |
| `docker-compose.yml` | RUNTIME_PASS cho SQL Server | `insurance_sqlserver` đang chạy; Airflow nằm trong profile deferred. |
| `notebooks/01-eda.ipynb` | RUNTIME_PASS | EDA thực tế đã tạo evidence trong `reports/data/`. |

Chi tiết về các cột nguồn được quản lý tại [data-dictionary.md](data-dictionary.md) và source contract chính thức nằm tại [source-data-contract.md](source-data-contract.md).
