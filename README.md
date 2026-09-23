# Motor Insurance Data Warehouse

Đây là dự án cá nhân xây dựng nền tảng Data Warehouse cho phân tích phí bảo hiểm, mức độ phơi nhiễm rủi ro và bồi thường xe cơ giới tại Brazil. Nền tảng đích dùng SQL Server, có staging theo batch, kiểm tra chất lượng dữ liệu, mô hình dimensional và các bước mở rộng sau này như điều phối, tối ưu hiệu năng, Machine Learning và Power BI.

## Nguồn dữ liệu chuẩn

Nguồn duy nhất của pipeline hiện tại là `brvehins1` trong `data/raw/brvehins1/`:

- `brvehins1a.csv`
- `brvehins1b.csv`
- `brvehins1c.csv`
- `brvehins1d.csv`
- `brvehins1e.csv`

Năm phân vùng có cùng header gồm 23 cột về người lái, xe, địa lý, exposure, phí, giá trị bảo hiểm, số vụ và số tiền bồi thường. Tổng số dòng đã được kiểm đếm ở mức file là 1,965,355 dòng; EDA sẽ xác minh và mô tả đầy đủ các đặc tính dữ liệu trước khi thiết kế database.

`data/raw/susep.gov.br/insurance_dataset.csv` là dữ liệu **LEGACY / NON-CANONICAL**. File được bảo toàn để tham chiếu lịch sử, không được join, stage hoặc dùng trong pipeline chuẩn.

## Kiến trúc mục tiêu

```text
Raw CSV bất biến
    -> Staging theo batch có metadata và đối soát
    -> Dimension và Fact dựa trên grain thực tế
    -> Data Quality gate
    -> Các giai đoạn sau: orchestration, ML, tuning, Power BI
```

Thiết kế chỉ được chốt sau EDA và source data contract. Dataset không có mã định danh khách hàng hoặc hợp đồng đã được chứng minh; dự án không được tự tạo business identifier. Nếu cần nhận diện kỹ thuật, hệ thống sẽ dùng khóa kỹ thuật có lineage về file nguồn và dòng nguồn.

## Trạng thái hiện tại

| Phân hệ | Trạng thái | Ghi chú |
|---|---|---|
| Raw `brvehins1` | STATIC_PASS | Có đủ năm file, header đồng nhất; raw là bất biến. |
| Governance và validation | DONE | `P1-WF-04` chuẩn hóa tài liệu và static validator. |
| EDA | RUNTIME_PASS | Profile streaming đã tạo bằng chứng cho toàn bộ 1,965,355 dòng. |
| Data contract | DONE | 23 cột, grain, technical identity và policy DQ đã được đóng băng. |
| Docker và SQL Server | RUNTIME_PASS | Container `insurance_sqlserver` chạy và `sqlcmd` kết nối thành công. |
| Migration bootstrap | RUNTIME_PASS | `V1__create_dwh_schema.sql` tạo `DWH_Insurance`, schemas/meta tables và rerun an toàn. |
| Staging | RUNTIME_PASS | Năm partition đã nạp: 1,965,355 rows, batch metadata và rerun idempotent có bằng chứng. |
| DWH, DQ | STALE SCAFFOLD — REQUIRES REFACTOR | Chưa có dimensional model/fact/DQ gate thực; sẽ được thay theo contract. |
| ML và Airflow | STALE SCAFFOLD — REQUIRES REFACTOR | Được hoãn đến sau nền tảng DWH và DQ. |
| Performance và Power BI | SCAFFOLD | Chờ dữ liệu DWH thực tế. |

`STATIC_PASS` chỉ xác nhận kiểm tra tĩnh. `RUNTIME_PASS` chỉ được dùng khi lệnh đã chạy thành công với dữ liệu và bằng chứng thực tế.

## Kiểm tra tĩnh

Từ thư mục gốc repository, chạy:

```powershell
python scripts/validate_repo.py
python -m py_compile scripts/validate_repo.py ml/train_risk_model.py ml/predict_risk_batch.py dags/insurance_dwh_pipeline.py
docker compose config
git diff --check
```

Các lệnh trên không chứng minh SQL Server, DWH hay Airflow đang hoạt động. Hướng dẫn vận hành được cập nhật theo từng thành phần có bằng chứng runtime tại [docs/guides/how-to-run.md](docs/guides/how-to-run.md).

## Python dependencies

Host Python dùng `requirements.txt` cho profiling và staging loader; `requirements-dev.txt` thêm validator/notebook tooling. Airflow không được cài vào host vì DAG chạy trong image Docker riêng. Chi tiết import audit, lý do và version pin ở [python-dependencies.md](docs/architecture/python-dependencies.md).

## Trình tự nền tảng

1. `P1-WF-04`: chuẩn hóa nguồn chuẩn và validation.
2. `P1-DATA-01`: EDA thực tế, profile và đánh giá grain.
3. `P1-DATA-02`: đóng băng source data contract.
4. `P1-INFRA`: khởi tạo SQL Server và metadata nền tảng.
5. `P1-INGEST`: staging, đối soát và idempotency theo năm partition.
6. `P1-DWH`: dimensions và fact dựa trên dữ liệu thực tế.
7. `P1-DQ`: rule nguồn/staging, integrity kho dữ liệu và quality gate.

Tài liệu kiến trúc hiện hành nằm trong `docs/architecture/`; tiến độ lịch sử chỉ được append tại [log/progress-log.md](log/progress-log.md).
