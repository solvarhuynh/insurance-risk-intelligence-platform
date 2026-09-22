# Cách chạy lại dự án

## Trạng thái cần biết trước

Tại thời điểm viết tài liệu này, dự án đang ở **Giai đoạn 1 — Khảo sát & chuẩn bị dữ liệu thật** (kết hợp hoàn thiện Governance và Validation Layer). Mã nguồn hiện tại trong repository ở mức **SCAFFOLD** hoặc **STATIC_PASS**, chưa có bước nào đạt **RUNTIME_PASS**.

Tài liệu này phân biệt rạch ròi 2 nhóm thao tác:
1. **Kiểm tra tĩnh (Static Check)**: Các lệnh khả dụng ngay trong môi trường phát triển hiện tại, không yêu cầu dữ liệu lớn hay container đang chạy.
2. **Quy trình vận hành thực tế (Runtime Execution)**: Trình tự End-to-End theo kiến trúc mục tiêu, đòi hỏi hạ tầng Docker, SQL Server hoạt động và tập dữ liệu thô đã tải về.

---

## 0. Các lệnh kiểm tra tĩnh (Khả dụng ngay)

Các lệnh sau dùng để xác thực cú pháp và tính toàn vẹn cấu hình mà không cần khởi động hạ tầng:

1. Kiểm tra cú pháp Python (DAG Airflow và module ML):
   ```powershell
   python -m py_compile dags/insurance_dwh_pipeline.py ml/train_risk_model.py ml/predict_risk_batch.py
   ```
   *Trạng thái*: `STATIC_PASS` — các tệp mã nguồn tuân thủ đúng cú pháp Python AST.

2. Kiểm tra tính hợp lệ của tệp Docker Compose:
   ```powershell
   docker compose config
   ```
   *Trạng thái*: `STATIC_PASS` — cấu trúc dịch vụ `sqlserver` và `airflow` được parse thành công.

---

## 1. Cài các công cụ cần thiết

1. Cài Docker Desktop và bật WSL 2. Docker cần có tối thiểu 6 GB RAM cho SQL Server và Airflow; 8 GB trở lên là mức khuyến nghị.
2. Cài một công cụ SQL: Azure Data Studio, SSMS hoặc `sqlcmd`.
3. Cài Python (≥3.10) với các thư viện: `pandas`, `scikit-learn`, `lightgbm`, `pyodbc`.
4. Cài Power BI Desktop để mở dashboard khi Giai đoạn 8 hoàn tất.

## 2. Chuẩn bị dữ liệu thô
*Trạng thái hiện tại*: `SCAFFOLD` / `BLOCKED` (chờ tải dữ liệu thực tế vào `data/raw/`)
*Trạng thái hiện tại*: `STATIC_PASS` (Dataset canonical đã sẵn sàng tại `data/raw/brvehins1/`; file legacy SUSEP được bảo lưu)

1. Tải 2 bộ dữ liệu:
   - Brazilian Insurance Market Data (SUSEP, ~8.3M dòng).
   - Porto Seguro's Safe Driver Prediction (Kaggle, ~1.5M dòng).
2. Đặt các file CSV vào `data/raw/`. Thư mục này không được commit dữ liệu lớn theo `.gitignore`.
3. Mở và chạy `notebooks/01-eda.ipynb`; điền kết quả cột, kiểu dữ liệu và vấn đề chất lượng vào `docs/architecture/data-dictionary.md`.
4. Cập nhật tên file CSV trong `sql/01_load_staging.sql` để khớp file đã tải.
1. Dataset canonical của dự án:
   - `data/raw/brvehins1/` gồm 5 partition CSV (`brvehins1a.csv` đến `brvehins1e.csv`), tổng cộng 1,965,355 dòng, 23 cột.
   - Đã được kiểm tra tính hiện diện và cấu trúc header đồng nhất bằng `python scripts/validate_repo.py`.
2. Dataset legacy (phi canonical):
   - `data/raw/susep.gov.br/insurance_dataset.csv` (~8.3M dòng, ~751 MB) được lưu giữ như tài liệu lịch sử, không tham gia vào pipeline canonical.
3. Mở và chạy `notebooks/01-eda.ipynb` để khảo sát phân bố dữ liệu `brvehins1`; thông số cột và kiểu dữ liệu chuẩn đã được lập tại `docs/architecture/data-dictionary.md`.

## 3. Khởi động SQL Server và Airflow
*Trạng thái hiện tại*: `STATIC_PASS` (cấu hình YAML sẵn sàng; cần môi trường Docker runtime để chạy)

Từ thư mục gốc repository, chạy:

```powershell
docker-compose up -d
docker-compose ps
```

Cấu hình nằm tại `docker-compose.yml`:
- SQL Server: `localhost,1433`, container `insurance_sqlserver`.
- Airflow: `http://localhost:8080`, container `insurance_airflow_webserver` và `insurance_airflow_scheduler`.
- Dữ liệu thô được mount từ `data/raw/` vào container SQL Server.

## 4. Tạo staging và nạp CSV
*Trạng thái hiện tại*: `SCAFFOLD` (kịch bản DDL và BULK INSERT ở dạng stub comment; đòi hỏi runtime SQL Server và dữ liệu CSV thật)
*Trạng thái hiện tại*: `SCAFFOLD` (kịch bản hiện tại `sql/01_load_staging.sql` là `STALE SCAFFOLD`, cần refactor cho 23 cột của `brvehins1`; đòi hỏi runtime SQL Server)

1. Kết nối SQL Server bằng Azure Data Studio/SSMS đến `localhost,1433` với tài khoản `sa`.
2. Mở và chạy `sql/01_load_staging.sql`.
3. Đối chiếu số dòng staging với số dòng từng CSV gốc.
2. Tạo database `Staging_InsuranceRaw` và bảng staging cho `brvehins1`.
3. Chạy lệnh `BULK INSERT` nạp 5 partition `brvehins1[a-e].csv`.
4. Đối chiếu số dòng staging đạt đúng 1,965,355 dòng khớp với dữ liệu gốc.

## 5. Chạy schema migration
*Trạng thái hiện tại*: `SCAFFOLD` (`migrations/V1__create_dwh_schema.sql` ở dạng stub comment; đòi hỏi cấu hình Flyway/DbUp và runtime SQL Server)
*Trạng thái hiện tại*: `SCAFFOLD` (tệp `migrations/V1__create_dwh_schema.sql` hiện tại là `STALE SCAFFOLD`, cần refactor theo Star Schema của `brvehins1`)

1. Áp dụng migration tại `migrations/V1__create_dwh_schema.sql` (bằng Flyway hoặc DbUp) để tạo database `DWH_Insurance` cùng 8 bảng Fact/Dim:
   - `Dim_Date`, `Dim_Region`, `Dim_Policy`, `Dim_Customer` (SCD2).
   - `Fact_Premium`, `Fact_Claims`, `Fact_Customer_Risk_Prediction`.
1. Áp dụng migration (bằng Flyway hoặc DbUp) để tạo database `DWH_Insurance` cùng các bảng Fact/Dim theo mô hình xe cơ giới:
   - Dimensions: `Dim_Driver_Profile`, `Dim_Vehicle`, `Dim_Geography`.
   - Facts: `Fact_Policy_Risk` (hoặc `Fact_Vehicle_Policy_Performance`), `Fact_Vehicle_Risk_Prediction`.

## 6. Bật CDC và chạy ETL
*Trạng thái hiện tại*: `SCAFFOLD` (toàn bộ stored procedure ở dạng khung stub với MERGE comment; đòi hỏi runtime SQL Server)
## 6. Xử lý gia tăng và chạy ETL
*Trạng thái hiện tại*: `SCAFFOLD` (các stored procedure `sql/02_enable_cdc.sql` đến `sql/06_sp_fact_claims.sql` là `STALE SCAFFOLD`, cần refactor theo schema mới)

Theo thứ tự, chạy các file sau trên SQL Server:
1. `sql/02_enable_cdc.sql` để bật CDC và tạo `ETL_Watermark`.
2. `sql/03_sp_dim_customer_scd2.sql` để tạo thủ tục nạp khách hàng có lịch sử.
3. `sql/04_sp_dim_others.sql` để tạo thủ tục nạp các Dimension khác.
4. `sql/05_sp_fact_premium.sql` và `sql/06_sp_fact_claims.sql` để tạo thủ tục nạp Fact.
5. `sql/07_data_quality_checks.sql` để tạo bảng log và thủ tục kiểm tra chất lượng.
6. `sql/08_sp_load_risk_predictions.sql` để tạo thủ tục nạp điểm rủi ro ML.
Theo thứ tự, chạy các thủ tục trên SQL Server:
1. Thiết lập cơ chế kiểm soát nạp gia tăng / partition watermark và tạo `ETL_Watermark`.
2. Chạy thủ tục nạp các bảng Dimension (`Dim_Driver_Profile`, `Dim_Vehicle`, `Dim_Geography`).
3. Chạy thủ tục nạp bảng Fact (`Fact_Policy_Risk`) với lookup surrogate key và MERGE UPSERT.
4. Chạy `sql/07_data_quality_checks.sql` để kiểm tra toàn vẹn dữ liệu.
5. Chạy thủ tục nạp kết quả dự đoán rủi ro ML (`Fact_Vehicle_Risk_Prediction`).

## 7. Huấn luyện mô hình Machine Learning
*Trạng thái hiện tại*: `STATIC_PASS` / Chờ runtime (mã nguồn hợp lệ; hàm trích xuất là stub chờ kết nối dữ liệu thật)
*Trạng thái hiện tại*: `STATIC_PASS` / `STALE SCAFFOLD` (mã nguồn AST hợp lệ; hàm trích xuất là stub chờ refactor theo feature contract của `brvehins1`)

1. Chạy script huấn luyện baseline model:
   ```powershell
   python ml/train_risk_model.py
   ```
2. Model artifact sẽ được lưu tại `ml/risk_model.pkl`.

## 8. Chạy DAG Airflow
*Trạng thái hiện tại*: `STATIC_PASS` / Chờ runtime (DAG pass cú pháp; các task dùng operator stub, chờ kết nối hạ tầng thật)
*Trạng thái hiện tại*: `STATIC_PASS` / `STALE SCAFFOLD` (DAG pass cú pháp; các task dùng operator stub, chờ refactor theo luồng task mới)

1. Mở Airflow Webserver tại `http://localhost:8080`.
2. Bật DAG `insurance_dwh_pipeline` và kích hoạt chạy thủ công.
3. Xác nhận chuỗi task thực thi:
   `load_staging` -> các Dimension (song song) -> các Fact -> `run_data_quality_checks` -> `predict_customer_risk` -> `load_risk_predictions` -> `notify`.
   `load_staging` -> các Dimension (song song) -> Fact -> `run_data_quality_checks` -> `predict_vehicle_risk` -> `load_risk_predictions` -> `notify`.

## 9. Mở Power BI
*Trạng thái hiện tại*: `SCAFFOLD` (chưa có tệp `.pbix`; sẽ triển khai ở Giai đoạn 8)

1. Mở `powerbi/insurance-dashboard.pbix` bằng Power BI Desktop.
2. Kết nối tới `DWH_Insurance`, làm mới dữ liệu và kiểm tra các báo cáo Loss Ratio, xu hướng phí và rủi ro dự đoán.
2. Kết nối tới `DWH_Insurance`, làm mới dữ liệu và kiểm tra các báo cáo Loss Ratio theo bang, nhóm xe, và đối chiếu rủi ro dự đoán của mô hình với tổn thất thực tế.

---

## 10. Runtime validation checklist

Danh mục này quy định toàn bộ tiêu chí nghiệm thu vận hành thật (Runtime Validation). Mỗi bước chỉ được đánh dấu hoàn thành khi có bằng chứng thực tế từ môi trường đang chạy.

| STT | Phân hệ | Lệnh / Quy trình thực thi | Bằng chứng nghiệm thu mong đợi (Expected Evidence) | Trạng thái hiện tại |
|---|---|---|---|---|
| 1 | Infrastructure | `docker compose up -d` && `docker compose ps` | Container `insurance_sqlserver` và `insurance_airflow` ở trạng thái `running / healthy`; các cổng 1433 và 8080 phản hồi kết nối. | PENDING_RUNTIME |
| 2 | Migration | Chạy migration qua Flyway/DbUp (hoặc `sqlcmd -i migrations/V1__create_dwh_schema.sql`) | Database `DWH_Insurance` được tạo; 8 bảng Fact/Dim tồn tại trong `sys.tables` với cấu trúc khóa chính, surrogate key và data type chuẩn. | PENDING_RUNTIME |
| 3 | Staging | `sqlcmd -i sql/01_load_staging.sql` | `Staging_InsuranceRaw` có các bảng staging; số dòng nạp qua `BULK INSERT` đối chiếu khớp 100% với file CSV gốc (~8.3M dòng SUSEP, ~1.5M dòng Porto Seguro). | PENDING_RUNTIME |
| 4 | CDC | `sqlcmd -i sql/02_enable_cdc.sql` | `sys.sp_cdc_enable_db` và `sys.sp_cdc_enable_table` bật thành công; capture jobs hoạt động; `ETL_Watermark` ghi nhận LSN; rerun không reload toàn bộ mà chỉ xử lý net changes; watermark LSN tăng dần. | PENDING_RUNTIME |
| 5 | Dimension | `EXEC dbo.sp_Load_DimCustomer;` && `EXEC dbo.sp_Load_DimOthers;` | SCD2: Duy nhất 1 dòng `Is_Current = 1` cho mỗi `CustomerId`; các dải `Start_Date`/`End_Date` lịch sử không chồng lấn; Idempotency: chạy lại cùng batch liên tiếp không làm tăng row count Dim; `ETL_Audit_Log` ghi status `'SUCCESS'`. | PENDING_RUNTIME |
| 6 | Fact | `EXEC dbo.sp_Load_FactPremium;` && `EXEC dbo.sp_Load_FactClaims;` | Referential Integrity: Mọi Foreign Key (`CustomerKey`, `DateKey`, `PolicyKey`, `RegionKey`) map chuẩn vào Dim, không có orphan record (-1); đúng độ hạt nghiệp vụ; chạy lại cùng batch bảo toàn số liệu. | PENDING_RUNTIME |
| 2 | Migration | Chạy migration qua Flyway/DbUp (hoặc `sqlcmd -i migrations/V1__create_dwh_schema.sql`) | Database `DWH_Insurance` được tạo; các bảng Fact/Dim xe cơ giới tồn tại trong `sys.tables` với cấu trúc khóa chính, surrogate key và data type chuẩn. | PENDING_RUNTIME |
| 3 | Staging | `sqlcmd -i sql/01_load_staging.sql` | `Staging_InsuranceRaw` có các bảng staging; số dòng nạp qua `BULK INSERT` đối chiếu khớp 100% với 5 partition CSV `brvehins1` (tổng 1,965,355 dòng). | PENDING_RUNTIME |
| 4 | CDC / Batch Watermark | `sqlcmd -i sql/02_enable_cdc.sql` | Cơ chế nạp gia tăng hoạt động; `ETL_Watermark` ghi nhận partition/batch LSN; rerun không nạp trùng lặp; watermark tăng dần. | PENDING_RUNTIME |
| 5 | Dimension | `EXEC dbo.sp_Load_DimDriverProfile;` && `EXEC dbo.sp_Load_DimVehicle;` && `EXEC dbo.sp_Load_DimGeography;` | Bảng Dim lưu trữ đầy đủ thuộc tính; Idempotency: chạy lại cùng batch liên tiếp không làm tăng row count Dim; `ETL_Audit_Log` ghi status `'SUCCESS'`. | PENDING_RUNTIME |
| 6 | Fact | `EXEC dbo.sp_Load_FactPolicyRisk;` | Referential Integrity: Mọi Foreign Key (`DriverProfileKey`, `VehicleKey`, `GeographyKey`) map chuẩn vào Dim, không có orphan record (-1); các metric `ExposTotal`, `PremTotal`, claims count/amount khớp 100% staging; chạy lại cùng batch bảo toàn số liệu. | PENDING_RUNTIME |
| 7 | DQ | `EXEC dbo.sp_Run_DataQualityChecks;` | `DQ_Check_Log` ghi kết quả kiểm định cho từng rule (not null, unique, FK, range check); khi cố ý đưa bản ghi lỗi, procedure trả về status thất bại (`@Status = 'FAILED'`) và ngắt pipeline. | PENDING_RUNTIME |
| 8 | Airflow | `docker compose exec airflow airflow dags trigger insurance_dwh_pipeline` | Toàn bộ DAG kết thúc với trạng thái `success` trên Web UI `localhost:8080`; đúng thứ tự phụ thuộc (Staging -> Dim song song -> Fact -> DQ -> ML -> Load Predictions -> Notify). | PENDING_RUNTIME |
| 9 | ML | `python ml/train_risk_model.py` && `python ml/predict_risk_batch.py` | Sinh artifact `ml/risk_model.pkl` với ROC-AUC > 0.60; batch scoring sinh điểm rủi ro cho khách hàng mới; `sp_Load_CustomerRiskPredictions` nạp thành công vào `Fact_Customer_Risk_Prediction`. | PENDING_RUNTIME |
| 9 | ML | `python ml/train_risk_model.py` && `python ml/predict_risk_batch.py` | Sinh artifact `ml/risk_model.pkl`; batch scoring sinh điểm rủi ro cho các profile xe; nạp thành công vào bảng Fact dự đoán rủi ro. | PENDING_RUNTIME |
| 10 | Tuning | Query benchmark với `SET STATISTICS IO, TIME ON;` trước/sau index | Bảng đo lường ghi nhận Logical Reads và CPU/Elapsed Time giảm rõ rệt; ảnh chụp Execution Plan chuyển từ Clustered Index Scan sang Index Seek + Key Lookup. | PENDING_RUNTIME |
| 11 | Power BI | Mở `insurance-dashboard.pbix` và refresh data | Báo cáo hiển thị các visual: Loss Ratio theo bang, xu hướng phí theo quý, đối chiếu rủi ro dự đoán của mô hình với tổn thất thực tế khớp 100% dữ liệu DWH. | PENDING_RUNTIME |
| 11 | Power BI | Mở `insurance-dashboard.pbix` và refresh data | Báo cáo hiển thị các visual: Loss Ratio theo bang/nhóm xe, xu hướng phí, đối chiếu rủi ro dự đoán của mô hình với tổn thất thực tế khớp 100% dữ liệu DWH. | PENDING_RUNTIME |
