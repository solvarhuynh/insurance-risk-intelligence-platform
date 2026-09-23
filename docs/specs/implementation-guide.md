# Hướng dẫn triển khai nền tảng Motor Insurance DWH

## Mục tiêu hiện hành

Xây dựng nền tảng dữ liệu có thể kiểm chứng cho dataset chuẩn `brvehins1`: raw bất biến, staging theo batch, data contract, DWH dimensional, đối soát và Data Quality gate. SQL Server là runtime đích. Các phần orchestration, ML, performance tuning và Power BI chỉ bắt đầu khi foundation đã có bằng chứng runtime.

## Nguồn chuẩn

`data/raw/brvehins1/` chứa năm partition CSV có schema 23 cột đồng nhất. `data/raw/susep.gov.br/insurance_dataset.csv` là **LEGACY / NON-CANONICAL** và không được đưa vào bất kỳ bước canonical nào.

## Nguyên tắc thiết kế

- Không sửa raw và không suy diễn cột không có trong nguồn.
- Không tạo business identifier khi data contract không chứng minh có identifier đó.
- Khóa kỹ thuật phải truy vết được về file nguồn, dòng nguồn và batch.
- Mỗi stage chỉ đạt `RUNTIME_PASS` khi có lệnh, đầu vào, đầu ra và bằng chứng thực tế.
- Chạy lại batch phải được kiểm tra idempotency, không chỉ được giả định.
- Hard DQ rule phải chặn pipeline; quan sát đáng ngờ nhưng chưa có contract là warning hoặc business review.

## Lộ trình foundation

| Stage | Mục tiêu | Bằng chứng tối thiểu |
|---|---|---|
| P1-WF-04 | Chuẩn hóa nguồn và validator | Năm file, schema bằng nhau, current docs không hướng dẫn kiến trúc cũ. |
| P1-DATA-01 | EDA thực tế | DONE: row count, null, duplicate, range, distribution và grain assessment. |
| P1-DATA-02 | Source data contract | DONE: 23 cột, SQL mapping, technical key, policy null/duplicate/invalid. |
| P1-INFRA | SQL Server và bootstrap | DONE: container, kết nối, database, schemas và migration rerun an toàn. |
| P1-INGEST | Staging và batch load | Năm batch, đối soát, metadata và idempotency. |
| P1-DWH | Dimensions và fact | Grain chính xác, FK hợp lệ và staging-to-fact reconciliation. |
| P1-DQ | Quality gate | Hard rules pass và controlled invalid input fail an toàn. |

## Artifact cũ

Các file SQL, ML và DAG có từ trước ở trạng thái **STALE SCAFFOLD — REQUIRES REFACTOR**. Chúng được giữ lại để thay thế có kiểm soát trong từng stage; nội dung của chúng không xác định mô hình nghiệp vụ hiện tại.

## Definition of Done của foundation

Foundation chỉ `DONE` khi năm partition được nạp qua một đường ingest có đối soát, DWH có fact và dimensions dựa trên contract thực, DQ pass trên dữ liệu production và quality gate dừng được input lỗi có kiểm soát. Báo cáo checkpoint và `log/progress-log.md` phải ghi đúng bằng chứng từng stage.
