# Cấu trúc thư mục hiện tại

Tài liệu này giải thích repository đang được chia thành những khu vực nào, mỗi khu vực dùng để làm gì và phần nào đã có thật hoặc mới là khung. Cây bên dưới bỏ qua `.git/` và `.venv/` vì đó là dữ liệu quản lý phiên bản và môi trường Python cục bộ, không phải đầu ra của dự án.

## Cây thư mục

```text
insurance-dwh-project/
├── .cursor/rules/              # Quy tắc làm việc và kiểm tra trong môi trường phát triển
├── data/raw/                   # CSV dữ liệu gốc (SUSEP + Porto Seguro); hiện chỉ có .gitkeep
├── data/raw/
│   ├── brvehins1/              # CANONICAL SOURCE: 5 phân đoạn CSV (1.965.355 dòng, 23 cột)
│   │   ├── brvehins1a.csv
│   │   ├── brvehins1b.csv
│   │   ├── brvehins1c.csv
│   │   ├── brvehins1d.csv
│   │   └── brvehins1e.csv
│   └── susep.gov.br/           # LEGACY SOURCE: Không sử dụng trong pipeline canonical
│       └── insurance_dataset.csv
├── docs/                       # Hệ thống tài liệu phân theo nhóm chuyên biệt
│   ├── architecture/           # Kiến trúc và mô hình dữ liệu
│   ├── guides/                 # Hướng dẫn thực hành và thuật ngữ
│   ├── reports/                # Báo cáo insight và performance tuning
│   └── specs/                  # Tài liệu đặc tả và định hướng gốc
├── ml/                         # Machine learning training và batch prediction
│   ├── train_risk_model.py     # Script huấn luyện baseline model
│   └── predict_risk_batch.py   # Script batch scoring gọi bởi Airflow
│   ├── train_risk_model.py     # Script huấn luyện baseline model (stale scaffold)
│   └── predict_risk_batch.py   # Script batch scoring gọi bởi Airflow (stale scaffold)
├── dags/                       # DAG Airflow điều phối pipeline
│   └── insurance_dwh_pipeline.py
│   └── insurance_dwh_pipeline.py # DAG điều phối pipeline (stale scaffold)
├── log/                        # Nhật ký tiến độ và báo cáo review
│   ├── progress-log.md
│   └── review-report-2026-09-15.md
├── migrations/                 # Script thay đổi schema theo version
│   └── V1__create_dwh_schema.sql
│   └── V1__create_dwh_schema.sql # DDL Star Schema cũ (stale scaffold)
├── notebooks/                  # Notebook khảo sát dữ liệu (EDA)
│   └── 01-eda.ipynb
├── powerbi/                    # File dashboard Power BI; hiện chỉ có .gitkeep
├── scripts/                    # Kịch bản kiểm tra tự động và vận hành
│   └── validate_repo.py        # Static baseline validation cho toàn bộ repository
├── sql/                        # Script staging, CDC, ETL, data quality và ML load
├── sql/                        # Script staging, CDC, ETL, data quality và ML load (stale scaffold)
│   ├── 01_load_staging.sql
│   ├── 02_enable_cdc.sql
│   ├── 03_sp_dim_customer_scd2.sql
│   ├── 04_sp_dim_others.sql
│   ├── 05_sp_fact_premium.sql
│   ├── 06_sp_fact_claims.sql
│   ├── 07_data_quality_checks.sql
│   └── 08_sp_load_risk_predictions.sql
├── .gitignore                  # Quy tắc không đưa dữ liệu lớn và secret vào Git
├── docker-compose.yml          # Cấu hình các service SQL Server và Airflow
└── README.md                   # Trang giới thiệu tổng quan của repository
```

## Chức năng từng thư mục và file

| Đường dẫn | Chức năng | Trạng thái hiện tại |
|---|---|---|
| `.cursor/rules/` | Chứa quy tắc hỗ trợ quy trình làm việc, quản lý file/log, review Git, Python và bàn giao. | STATIC_PASS: Bộ quy tắc quản trị chuẩn hoá cho dự án cá nhân, đã kiểm tra regex/link sạch. |
| `data/raw/` | Nơi đặt các CSV nguyên bản tải từ SUSEP (~8.3M dòng) và Porto Seguro (~1.5M dòng). Dữ liệu ở đây được giữ nguyên để đối chiếu. | SCAFFOLD: Hiện chỉ có `.gitkeep`, chưa tải CSV thô (chờ Giai đoạn 1). |
| `data/raw/brvehins1/` | Nơi chứa 5 phân đoạn CSV canonical của `brvehins1` (1.965.355 dòng, 23 cột). Dữ liệu nguồn duy nhất cho pipeline. | STATIC_PASS: Đầy đủ 5 file, schema đồng nhất, bất biến. |
| `data/raw/susep.gov.br/` | Nơi lưu trữ file CSV báo cáo thị trường vĩ mô cũ của SUSEP. | LEGACY: Lưu trữ lịch sử, không tham gia vào pipeline canonical. |
| `docs/` | Nơi chứa tài liệu kiến trúc, thuật ngữ, data dictionary, cách chạy, insight, tuning và đặc tả nguồn. | STATIC_PASS: Đã cấu trúc thành 4 nhóm (`architecture/`, `guides/`, `reports/`, `specs/`), đã đối chiếu nội dung. |
| `ml/` | Chứa mã huấn luyện mô hình dự đoán rủi ro và mã batch scoring phục vụ pipeline tự động. | STATIC_PASS: `train_risk_model.py` và `predict_risk_batch.py` pass `py_compile`; hàm trích xuất/huấn luyện là stub chờ data. |
| `dags/` | Chứa mã DAG Airflow điều phối toàn bộ luồng ETL, DQ check và ML scoring. | STATIC_PASS: `insurance_dwh_pipeline.py` pass `py_compile`; các task hiện dùng operator stub, chưa chạy runtime. |
| `log/` | Lưu lịch sử công việc, trạng thái giai đoạn và các báo cáo kiểm tra. | STATIC_PASS: Có `progress-log.md` kèm snapshot 13 phân hệ và `review-report-2026-09-15.md`. |
| `migrations/` | Lưu các thay đổi cấu trúc Data Warehouse theo version (Flyway/DbUp). | SCAFFOLD: `V1__create_dwh_schema.sql` chứa DDL 8 bảng ở dạng block comment stub, chưa apply vào database. |
| `notebooks/` | Dùng cho phân tích khám phá dữ liệu (EDA): xem shape, kiểu dữ liệu, null, duplicate. | SCAFFOLD: `01-eda.ipynb` có cấu trúc JSON hợp lệ; chưa chạy với dữ liệu thật. |
| `ml/` | Chứa mã huấn luyện mô hình dự đoán rủi ro và mã batch scoring phục vụ pipeline tự động. | STATIC_PASS / STALE SCAFFOLD: Mã pass cú pháp Python AST; logic trích xuất thuộc scaffold cũ, chờ refactor theo brvehins1. |
| `dags/` | Chứa mã DAG Airflow điều phối toàn bộ luồng ETL, DQ check và ML scoring. | STATIC_PASS / STALE SCAFFOLD: Mã pass cú pháp Python AST; task dùng operator stub, chờ refactor theo brvehins1. |
| `log/` | Lưu lịch sử công việc, trạng thái giai đoạn và các báo cáo kiểm tra. | STATIC_PASS: Có `progress-log.md` kèm snapshot hiện trạng và `review-report-2026-09-15.md`. |
| `migrations/` | Lưu các thay đổi cấu trúc Data Warehouse theo version (Flyway/DbUp). | STALE SCAFFOLD: `V1__create_dwh_schema.sql` chứa DDL mẫu cũ; cần refactor theo brvehins1. |
| `notebooks/` | Dùng cho phân tích khám phá dữ liệu (EDA): xem shape, kiểu dữ liệu, null, duplicate. | SCAFFOLD: `01-eda.ipynb` có cấu trúc JSON hợp lệ; sẵn sàng cho task EDA thật `P1-DATA-01`. |
| `powerbi/` | Nơi lưu dashboard Power BI kết nối đến `DWH_Insurance`. | SCAFFOLD: Hiện chỉ có `.gitkeep`, chờ triển khai ở Giai đoạn 8. |
| `scripts/` | Chứa script vận hành và static baseline validator cho repo. | STATIC_PASS: `validate_repo.py` dùng stdlib + PyYAML kiểm tra toàn bộ static quality gates. |
| `sql/` | Chứa SQL theo thứ tự pipeline: nạp staging, bật CDC, nạp Dim/Fact, DQ checks và nạp kết quả ML. | SCAFFOLD: 8 file T-SQL ở dạng khung mẫu/stub với MERGE và block comment, chưa thực thi trên SQL Server. |
| `scripts/` | Chứa script vận hành và static baseline validator cho repo. | STATIC_PASS: `validate_repo.py` dùng stdlib + PyYAML kiểm tra toàn bộ 50 static quality gates. |
| `sql/` | Chứa SQL theo thứ tự pipeline: nạp staging, bật CDC, nạp Dim/Fact, DQ checks và nạp kết quả ML. | STALE SCAFFOLD: 8 file T-SQL ở dạng khung mẫu/stub cũ, cần refactor theo brvehins1. |
| `.gitignore` | Ngăn dữ liệu thô lớn, secret, cache Python và file tạm bị đưa vào Git. | STATIC_PASS: Đã cấu hình và kiểm tra loại trừ phù hợp. |
| `docker-compose.yml` | Mô tả môi trường chạy cục bộ gồm SQL Server và Airflow. | STATIC_PASS: Đã kiểm tra parse tĩnh YAML/compose; chưa khởi chạy container runtime. |
| `README.md` | Điểm bắt đầu cho người mới: mục tiêu, dữ liệu, kiến trúc, công nghệ, cây repo, cách chạy và trạng thái. | STATIC_PASS: Đã phân định rõ kiến trúc mục tiêu và bảng snapshot hiện trạng thực tế. |

## Quan hệ giữa các khu vực

Luồng dữ liệu đi từ `data/raw/` vào `sql/01_load_staging.sql`, qua các Stored Procedure `sql/02_...` đến `sql/07_...` để nạp vào Star Schema trong `migrations/`. DAG trong `dags/` điều phối các bước, kích hoạt module `ml/` để dự đoán rủi ro và nạp kết quả qua `sql/08_sp_load_risk_predictions.sql`. `powerbi/` là lớp tiêu thụ dữ liệu cuối cùng hiển thị báo cáo phân tích và đối chiếu rủi ro dự đoán.
