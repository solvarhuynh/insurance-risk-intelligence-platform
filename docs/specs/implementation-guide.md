# Implementation Guide — Insurance DWH, Performance Tuning & Machine Learning

> File này dùng để bạn (hoặc một AI coding assistant như Claude Code) đi theo từng bước, checklist rõ ràng, có tiêu chí hoàn thành (Definition of Done) cho mỗi giai đoạn. Đọc kèm file `insurance-dwh-overview.pdf` và hệ thống tài liệu trong `docs/` để hiểu bức tranh tổng thể.

## Mục tiêu dự án
Xây một Data Warehouse ngành bảo hiểm dùng **dữ liệu thật quy mô lớn (~10 triệu dòng, ~2.5 GB raw)**, trên **Microsoft SQL Server**, có luồng ETL bằng **T-SQL** với **incremental load (CDC)**, được điều phối bởi **Airflow**, có **audit log/idempotency** và **data quality tự động**, chứng minh khả năng **Performance Tuning**, tích hợp **Machine Learning Batch Prediction** (dự đoán xác suất rủi ro tổn thất), và một lớp **Power BI** với insight phân tích thật.
Xây một Data Warehouse ngành bảo hiểm dùng **dữ liệu thật quy mô lớn (~1.965 triệu dòng, ~302 MB CSV raw, 5 partitions)**, trên **Microsoft SQL Server**, có luồng ETL bằng **T-SQL** với **incremental load (CDC / partition watermark)**, được điều phối bởi **Airflow**, có **audit log/idempotency** và **data quality tự động**, chứng minh khả năng **Performance Tuning**, tích hợp **Machine Learning Batch Prediction** (dự đoán xác suất rủi ro tổn thất xe cơ giới), và một lớp **Power BI** với insight phân tích thật.

> So với bản DE "cơ bản", bản này thêm hẳn lớp *pipeline engineering* và *MLOps batch inference* — thứ phân biệt Data Engineer với Analytics Engineer: dữ liệu chảy vào hệ thống một cách tự động, chịu lỗi, không load lại toàn bộ mỗi lần, được giám sát và phục vụ trực tiếp cho mô hình AI/ML.

## Nguồn dữ liệu
| Bộ dữ liệu | Nguồn | Dùng cho |
|---|---|---|
| Brazilian Insurance Market Data (SUSEP) | Kaggle / susep.gov.br — dataset công khai do cơ quan quản lý bảo hiểm Brazil (SUSEP) công bố; ~8.3 triệu dòng, premium/claims theo công ty, sản phẩm, bang, tháng, từ 2003 | Fact_Premium, Fact_Claims |
| Porto Seguro's Safe Driver Prediction | Kaggle competition — dữ liệu bảo hiểm xe cơ giới Brazil thật, ~1.5 triệu dòng (train + test) | Dim_Customer, Feature Store cho Machine Learning (Claim Probability) |
| Brazilian Vehicle Insurance Dataset (`brvehins1`) — **Canonical** | CASdatasets / AUTOSEG / SUSEP ecosystem; `data/raw/brvehins1/brvehins1[a-e].csv` (5 partitions, 1,965,355 dòng, 23 cột) | Toàn bộ pipeline DWH canonical: staging, dimensions (driver, vehicle, geography), facts (exposure, premium, claims by risk type), ML feature store & batch prediction |
| Brazilian Insurance Market Data (`susep.gov.br`) — **Legacy / Non-canonical** | `data/raw/susep.gov.br/insurance_dataset.csv` (~8.3 triệu dòng, ~751 MB) | Lưu giữ như tài liệu lịch sử; **không** dùng cho pipeline canonical hiện tại |

> Lưu ý: 2 bộ dữ liệu này cùng bắt nguồn từ thị trường bảo hiểm Brazil, giúp dữ liệu có tính đồng nhất cao về bối cảnh địa lý và kinh tế. Tổng quy mô thô đạt ~2.0 — 2.5 GB CSV, khi nạp vào SQL Server kèm Staging, CDC và Index sẽ đạt ~5 — 6 GB database.
> Lưu ý: Dataset canonical `brvehins1` gồm 5 partition CSV (`brvehins1a.csv` đến `brvehins1e.csv`) có cấu trúc schema 23 cột hoàn toàn đồng nhất, bao phủ đầy đủ nghiệp vụ bảo hiểm xe cơ giới: thời gian chịu rủi ro (exposure), phí bảo hiểm (premium), giá trị bảo hiểm (sum insured), số vụ và số tiền bồi thường theo 5 loại rủi ro (robbery, partial collision, total collision, fire, other), phân nhóm theo đặc tính tài xế, xe và địa lý. Mã nguồn scaffold cũ (SQL, ML, DAG) được đánh dấu `STALE SCAFFOLD` và sẽ được tái cấu trúc theo data contract của `brvehins1`.

---

## Quy ước trạng thái & Nguyên tắc Definition of Done

Mỗi giai đoạn trong tài liệu này có một danh sách **Definition of Done (DoD)**. Để đảm bảo tính trung thực kỹ thuật và phản ánh chính xác tiến độ, dự án áp dụng nghiêm ngặt các quy ước trạng thái sau:

### Bộ từ vựng trạng thái chuẩn:
- `SCAFFOLD`: Mới tạo khung file, thư mục, stub code, block comment hoặc template; chưa được cấu hình hay thực thi. Việc tạo một file stub **KHÔNG** đủ điều kiện để tích hoàn thành các mục đòi hỏi vận hành.
- `STATIC_PASS`: Mã nguồn hoặc tài liệu đã vượt qua các bước kiểm tra tĩnh (linter, syntax check bằng `py_compile`, parse YAML/JSON/Compose, đối chiếu schema/DDL cân bằng comment, không có cú pháp lỗi).
- `RUNTIME_PASS`: Mã nguồn, truy vấn SQL, container hoặc pipeline đã thực sự chạy thành công trong môi trường thực thi (Docker, SQL Server, Airflow, Python) với dữ liệu đầu vào và kết quả đầu ra thực tế được kiểm chứng.
- `BLOCKED`: Công việc tạm thời không thể tiếp tục do thiếu điều kiện tiên quyết (ví dụ: chưa tải dữ liệu thô, chưa khởi động container hạ tầng, thiếu thư viện).
- `DONE`: Chỉ đánh dấu khi toàn bộ các tiêu chí nghiệm thu của một task workflow hoặc một giai đoạn đã hoàn tất trọn vẹn theo đúng Definition of Done.
- `FAILED`: Quá trình kiểm tra tĩnh hoặc chạy runtime phát sinh lỗi, cần khắc phục.

### Nguyên tắc xác thực:
1. **Phân biệt rạch ròi giữa tạo file và xác thực vận hành**:
   - Một file script SQL hoặc DAG Python mới ở dạng template/stub chỉ được ghi nhận là `SCAFFOLD` (hoặc `STATIC_PASS` nếu đã kiểm tra cú pháp).
   - Mục DoD nào yêu cầu "chạy thành công", "nạp dữ liệu", "đối chiếu row count", "kết nối được" BẮT BUỘC phải đạt `RUNTIME_PASS` trên môi trường thật mới được đánh dấu tick `[x]`.
2. **Không đánh dấu hoàn thành sớm**: Tuyệt đối không tích chọn các mục Definition of Done khi mới chỉ tạo khung file mà chưa thực thi xác minh thực tế.

---

## Giai đoạn 1 — Khảo sát & chuẩn bị dữ liệu thật

**Việc cần làm:**
1. Tải 2 bộ dữ liệu về `data/raw/`.
2. Dùng Python (pandas) đọc và khảo sát nhanh: số dòng, số cột, kiểu dữ liệu, tỷ lệ null, giá trị trùng lặp, khoảng thời gian dữ liệu bao phủ.
3. Ghi lại data dictionary (mô tả từng cột) cho cả 2 bộ tại `docs/architecture/data-dictionary.md` — làm cơ sở thiết kế schema ở Giai đoạn 3.
4. Xác định các vấn đề chất lượng dữ liệu cần xử lý (encoding, định dạng ngày tháng, đơn vị tiền tệ BRL, mã hoá category ở bộ Porto Seguro).
1. Dữ liệu canonical đã sẵn sàng tại `data/raw/brvehins1/` gồm 5 partition CSV (`brvehins1a.csv` đến `brvehins1e.csv`, tổng cộng 1,965,355 dòng, 23 cột). File `data/raw/susep.gov.br/insurance_dataset.csv` là legacy, không dùng cho pipeline canonical.
2. Dùng Python (pandas) đọc và khảo sát: số dòng, số cột, kiểu dữ liệu, tỷ lệ null, giá trị trùng lặp, độ bao phủ các nhóm xe và địa lý.
3. Hoàn thiện data dictionary (mô tả 23 cột) tại `docs/architecture/data-dictionary.md` — làm cơ sở thiết kế schema ở Giai đoạn 3.
4. Xác định các vấn đề chất lượng dữ liệu cần xử lý (kiểu dữ liệu số/chuỗi, mã hóa category, phân bố exposure và claim count).

**Definition of Done:**
- [ ] File `docs/architecture/data-dictionary.md` mô tả từng cột của 2 bộ dữ liệu gốc.
- [ ] File `notebooks/01-eda.ipynb` (hoặc script) chứa kết quả khảo sát (shape, null %, sample rows).
- [x] File `docs/architecture/data-dictionary.md` mô tả chi tiết 23 cột của dataset canonical `brvehins1`.
- [ ] File `notebooks/01-eda.ipynb` (hoặc script EDA) chứa kết quả khảo sát (shape, null %, sample rows, distribution).
- [ ] Danh sách vấn đề chất lượng dữ liệu đã ghi nhận.

---

## Giai đoạn 2 — Hạ tầng & Staging

**Việc cần làm:**
1. Viết `docker-compose.yml` dựng **2 service**: SQL Server 2022 (`mcr.microsoft.com/mssql/server`) và Airflow (webserver + scheduler, dùng image `apache/airflow`). Cấp đủ RAM (khuyến nghị ≥6GB tổng cho cả 2 container).
2. Kết nối SQL Server bằng Azure Data Studio hoặc `sqlcmd`/`mssql-cli` từ WSL để xác nhận kết nối OK; kiểm tra Airflow UI truy cập được qua `localhost:8080`.
3. Tạo database `Staging_InsuranceRaw`.
4. Tạo bảng staging khớp cấu trúc CSV gốc (không transform).
5. Nạp dữ liệu bằng `BULK INSERT` (từ file CSV đã convert phù hợp) — **không** insert từng dòng qua Python/pyodbc vì quá chậm với hàng triệu dòng.
6. Kiểm tra số dòng nạp vào khớp với số dòng file gốc.
4. Tạo bảng staging khớp cấu trúc 23 cột của `brvehins1` (không transform).
5. Nạp dữ liệu bằng `BULK INSERT` (từ 5 partition CSV `brvehins1[a-e].csv`) — **không** insert từng dòng qua Python/pyodbc vì quá chậm với hàng triệu dòng.
6. Kiểm tra số dòng nạp vào khớp với 1,965,355 dòng của 5 partition gốc.

> Lưu ý: File `sql/01_load_staging.sql` hiện tại ở trạng thái `STALE SCAFFOLD` (scaffold theo mô hình cũ), cần refactor trong task triển khai staging cho `brvehins1`.

**Definition of Done:**
- [ ] `docker-compose.yml` chạy được cả SQL Server và Airflow, ổn định.
- [ ] Database `Staging_InsuranceRaw` có đủ bảng staging tương ứng 2 nguồn dữ liệu.
- [ ] Script `sql/01_load_staging.sql` (hoặc `.py` gọi BULK INSERT) chạy thành công, log số dòng nạp.
- [ ] Đối chiếu row count staging = row count file CSV gốc.
- [ ] Database `Staging_InsuranceRaw` có bảng staging tương ứng dataset canonical `brvehins1`.
- [ ] Script `sql/01_load_staging.sql` (hoặc script nạp tương đương) chạy thành công, log số dòng nạp.
- [ ] Đối chiếu row count staging = 1,965,355 dòng của 5 partition CSV gốc.

---

## Giai đoạn 3 — Thiết kế Data Warehouse & Schema Migration

**Việc cần làm:**
1. Thiết kế ERD cho Star Schema (dùng draw.io / dbdiagram.io), gồm:
   - **Fact_Premium**: khoá ngoại tới Dim_Customer, Dim_Policy, Dim_Date, Dim_Region; số đo: giá trị phí, số hợp đồng.
   - **Fact_Claims**: khoá ngoại tương tự; số đo: giá trị bồi thường, số vụ claim.
   - **Fact_Customer_Risk_Prediction**: bảng lưu trữ kết quả scoring dự đoán từ mô hình Machine Learning.
   - **Dim_Customer**: áp dụng **SCD Type 2** (cột `Start_Date`, `End_Date`, `Is_Current`) — nếu thuộc tính khách hàng thay đổi, thêm dòng mới thay vì ghi đè.
   - **Dim_Policy**: loại sản phẩm bảo hiểm, đặc điểm hợp đồng.
   - **Dim_Date**: bảng ngày chuẩn (ngày, tháng, quý, năm) để dễ phân tích theo thời gian.
   - **Dim_Region**: bang/khu vực (từ dữ liệu SUSEP).
1. Thiết kế ERD cho Star Schema (dùng draw.io / dbdiagram.io) dựa trên cấu trúc nghiệp vụ của `brvehins1`:
   - Lưu ý quan trọng: Dữ liệu `brvehins1` không có `CustomerId`, `PolicyNumber`, ngày giao dịch cụ thể, hay chu kỳ hiệu lực khách hàng SCD2. Mô hình được tổ chức theo chiều tài xế, xe, địa lý và rủi ro:
   - **Fact_Policy_Risk** (hoặc Fact biểu diễn rủi ro/hiệu quả bảo hiểm xe): khoá ngoại tới `Dim_Driver_Profile`, `Dim_Vehicle`, `Dim_Geography`; các metric: `ExposTotal`, `ExposFireRob`, `PremTotal`, `PremFireRob`, `SumInsAvg`, số vụ và tổn thất claim theo 5 loại rủi ro (Robbery, Partial Collision, Total Collision, Fire, Other).
   - **Fact_Vehicle_Risk_Prediction**: bảng lưu trữ kết quả scoring rủi ro từ mô hình Machine Learning.
   - **Dim_Driver_Profile**: nhóm tuổi tài xế (`DrivAge`), giới tính (`Gender`).
   - **Dim_Vehicle**: năm xe (`VehYear`), model xe (`VehModel`), nhóm xe (`VehGroup`).
   - **Dim_Geography**: khu vực (`Area`), bang (`State`, `StateAb`).
2. Cài đặt công cụ **Schema Migration** (Flyway hoặc DbUp) — mọi script tạo/sửa bảng đều là 1 file migration đánh version tăng dần (`V1__create_dwh_schema.sql`, `V2__...`), không chạy tay ALTER TABLE.
3. Viết migration đầu tiên tạo database `DWH_Insurance` và toàn bộ bảng Fact/Dim với khoá chính, khoá ngoại rõ ràng.
3. Viết migration tạo database `DWH_Insurance` và toàn bộ bảng Fact/Dim với khoá chính, khoá ngoại rõ ràng.
4. Xác định business key vs surrogate key cho từng Dim.

> Lưu ý: File `migrations/V1__create_dwh_schema.sql` hiện tại ở trạng thái `STALE SCAFFOLD` (scaffold theo mô hình cũ có Dim_Customer SCD2), cần refactor trong task thiết kế schema mới.

**Definition of Done:**
- [ ] File ERD (ảnh hoặc link draw.io) lưu trong `docs/architecture/erd.png`.
- [ ] Thư mục `migrations/` chứa các file `.sql` đánh version, chạy được qua Flyway/DbUp từ trạng thái rỗng.
- [ ] Mỗi bảng Dim có surrogate key (identity) + business key gốc.
- [ ] Dim_Customer có đủ cột SCD Type 2.
- [ ] Mỗi bảng Dim có surrogate key (identity) + business/natural key gốc.
- [ ] README trong `migrations/` mô tả cách chạy migration để dựng lại DWH từ đầu.

---

## Giai đoạn 4 — ETL bằng T-SQL với Incremental Load & Audit Log

**Việc cần làm:**

**4a. Incremental Load bằng Change Data Capture (CDC)**
1. Bật CDC trên các bảng Staging liên quan (`EXEC sys.sp_cdc_enable_db`, `EXEC sys.sp_cdc_enable_table`).
2. Tạo bảng control `ETL_Watermark` lưu LSN/timestamp lần chạy gần nhất cho từng bảng.
3. Viết Stored Procedure dùng `cdc.fn_cdc_get_net_changes_<capture_instance>` để lấy đúng phần dữ liệu mới/thay đổi kể từ watermark trước đó, thay vì đọc lại toàn bộ bảng.
**4a. Incremental Load / Partition Processing**
1. Xây dựng cơ chế xử lý nạp theo từng partition hoặc watermark (ví dụ nạp lần lượt partition `a` đến `e` hoặc theo watermark batch).
2. Tạo bảng control `ETL_Watermark` lưu partition/batch_id/timestamp lần chạy gần nhất.
3. Viết Stored Procedure xử lý nạp dữ liệu gia tăng, bảo đảm chỉ xử lý phần dữ liệu mới chưa nạp.

**4b. Audit Log & Idempotency**
4. Tạo bảng `ETL_Audit_Log`: `batch_id, procedure_name, start_time, end_time, rows_affected, status, error_message`.
5. Wrap mỗi Stored Procedure bằng `TRY...CATCH`, ghi log kể cả khi lỗi (status = 'FAILED', error_message chi tiết).
6. Thiết kế toàn bộ Stored Procedure UPSERT bằng `MERGE`, đảm bảo chạy lại cùng batch không tạo dòng trùng — test bằng cách chạy 2 lần liên tiếp và so sánh row count.

**4c. Stored Procedures chính**
7. `sp_Load_DimCustomer` — xử lý logic SCD Type 2 dựa trên CDC net changes từ Porto Seguro.
8. Stored Procedure cho các Dim còn lại (đơn giản hơn — UPSERT bằng `MERGE`).
9. `sp_Load_FactPremium`, `sp_Load_FactClaims` — join dữ liệu CDC với các Dim để lấy surrogate key, `MERGE` UPSERT vào Fact.
10. Viết vài query kiểm tra referential integrity: mọi dòng Fact đều join được với Dim tương ứng, không có "unknown member" bất thường.
7. `sp_Load_DimDriverProfile`, `sp_Load_DimVehicle`, `sp_Load_DimGeography` — UPSERT bằng `MERGE` vào các Dimension.
8. `sp_Load_FactPolicyRisk` — join dữ liệu staging với các Dim để lấy surrogate key, `MERGE` UPSERT vào Fact.
9. Viết query kiểm tra referential integrity: mọi dòng Fact đều join được với Dim tương ứng, không có "unknown member" bất thường.

> Lưu ý: Các script SQL hiện tại (`sql/02_enable_cdc.sql`, `sql/03_sp_dim_customer_scd2.sql` đến `sql/06_sp_fact_claims.sql`) là `STALE SCAFFOLD` và sẽ được refactor theo schema mới.

**Definition of Done:**
- [ ] CDC bật thành công trên bảng Staging, `sql/02_enable_cdc.sql` ghi lại các lệnh setup.
- [ ] `ETL_Watermark` cập nhật đúng sau mỗi lần chạy; chạy incremental chỉ xử lý phần thay đổi.
- [ ] Cơ chế incremental / batch load hoạt động, script setup ghi lại đầy đủ.
- [ ] `ETL_Watermark` cập nhật đúng sau mỗi lần chạy; chạy incremental chỉ xử lý phần thay đổi/partition mới.
- [ ] `ETL_Audit_Log` có dữ liệu đầy đủ sau mỗi lần chạy, kể cả trường hợp lỗi.
- [ ] Chạy lại cùng batch 2 lần liên tiếp → row count Fact/Dim không đổi (chứng minh idempotent).
- [ ] `sql/03_sp_dim_customer_scd2.sql`, `sql/04_sp_dim_others.sql`, `sql/05_sp_fact_premium.sql`, `sql/06_sp_fact_claims.sql`.
- [ ] Toàn bộ Stored Procedure ETL cho Dim và Fact được hoàn thiện và kiểm thử.
- [ ] Query kiểm tra referential integrity không phát hiện bản ghi mồ côi (orphan).

---

## Giai đoạn 5 — Data Quality Framework

**Việc cần làm:**
1. Định nghĩa bộ rule kiểm định chất lượng dữ liệu:
   - Not null trên các cột khoá bắt buộc.
   - Unique trên business key của từng Dim.
   - Unique trên natural/business key của từng Dim.
   - Referential integrity: mọi FK trong Fact phải tồn tại trong Dim tương ứng.
   - Giá trị hợp lý: số tiền phí/bồi thường không âm, ngày hợp đồng nằm trong khoảng hợp lý.
   - Giá trị hợp lý: số tiền phí/bồi thường không âm, exposure >= 0, tổng claim amount >= 0.
2. Tạo bảng `DQ_Check_Log`: `check_name, run_time, table_name, rows_checked, rows_failed, status`.
3. Viết Stored Procedure `sp_Run_DataQualityChecks` chạy toàn bộ rule, ghi kết quả vào `DQ_Check_Log`.
4. Nếu có check quan trọng fail (VD: orphan record), procedure trả về status lỗi để bước Airflow phía sau biết dừng pipeline và cảnh báo.

**Definition of Done:**
- [ ] `sql/07_data_quality_checks.sql` chứa toàn bộ rule kiểm định.
- [ ] `sql/07_data_quality_checks.sql` chứa toàn bộ rule kiểm định (cần refactor theo schema brvehins1).
- [ ] `DQ_Check_Log` có dữ liệu sau mỗi lần chạy.
- [ ] Test thử bằng cách cố tình đưa 1 dòng dữ liệu lỗi vào staging, xác nhận check phát hiện đúng và ghi log fail.

---

## Giai đoạn 6 — Orchestration & Machine Learning Pipeline

**Việc cần làm:**
1. Viết script huấn luyện baseline model `ml/train_risk_model.py` và script batch prediction `ml/predict_risk_batch.py`.
2. Viết Stored Procedure `sql/08_sp_load_risk_predictions.sql` để nạp kết quả dự đoán vào `Fact_Customer_Risk_Prediction`.
1. Viết script huấn luyện baseline model `ml/train_risk_model.py` và script batch prediction `ml/predict_risk_batch.py` dự đoán xác suất rủi ro xe cơ giới (ví dụ: Claim Occurrence / Claim Frequency từ đặc tính xe, tài xế, exposure).
2. Viết Stored Procedure `sql/08_sp_load_risk_predictions.sql` để nạp kết quả dự đoán vào `Fact_Vehicle_Risk_Prediction`.
3. Viết DAG Airflow (`dags/insurance_dwh_pipeline.py`) mô tả luồng phụ thuộc:
   - Task `load_staging` (BULK INSERT CDC net changes)
   - Task `load_dim_customer`, `load_dim_policy`, `load_dim_date`, `load_dim_region` (chạy song song)
   - Task `load_fact_premium`, `load_fact_claims` (phụ thuộc các task Dim)
   - Task `run_data_quality_checks` (phụ thuộc các task Fact)
   - Task `predict_customer_risk` (chạy batch scoring từ ML model)
   - Task `load_staging` (BULK INSERT theo partition)
   - Task `load_dim_driver_profile`, `load_dim_vehicle`, `load_dim_geography` (chạy song song)
   - Task `load_fact_policy_risk` (phụ thuộc các task Dim)
   - Task `run_data_quality_checks` (phụ thuộc task Fact)
   - Task `predict_vehicle_risk` (chạy batch scoring từ ML model)
   - Task `load_risk_predictions` (nạp kết quả ML vào DWH)
   - Task `notify` — gửi thông báo kết quả
4. Cấu hình `retries=3`, `retry_delay` và `on_failure_callback`.

> Lưu ý: Các file `ml/*.py`, `sql/08_sp_load_risk_predictions.sql` và `dags/insurance_dwh_pipeline.py` hiện tại là `STALE SCAFFOLD` chờ data contract tại task P1-DATA-01.

**Definition of Done:**
- [ ] `dags/insurance_dwh_pipeline.py` xuất hiện và chạy được trên Airflow UI (`localhost:8080`).
- [ ] Graph view thể hiện đúng dependency (Dim song song -> Fact -> DQ check -> ML scoring -> Load Predictions -> Notify).
- [ ] Kết quả dự đoán được ghi nhận đầy đủ trong `Fact_Customer_Risk_Prediction`.
- [ ] Kết quả dự đoán được ghi nhận đầy đủ trong bảng Fact rủi ro.

---

## Giai đoạn 7 — Performance Tuning & Tài liệu hoá

**Việc cần làm:**
1. Viết 2-3 câu query phân tích nghiệp vụ thực tế trên Fact tables (~8-10 triệu dòng).
1. Viết 2-3 câu query phân tích nghiệp vụ thực tế trên Fact tables (~1.965 triệu dòng).
2. Đo Execution Plan và `SET STATISTICS IO, TIME ON` khi chưa có index.
3. Tạo Non-Clustered / Covering Index và partition theo tháng/năm.
3. Tạo Non-Clustered / Covering Index và partition theo nhóm xe / bang.
4. Chạy lại query, chụp lại Execution Plan + STATISTICS IO, so sánh trước/sau.
5. Tổng hợp báo cáo tại `docs/reports/performance-tuning-summary.md` và `README.md`.

**Definition of Done:**
- [ ] Ít nhất 2 query nghiệp vụ có kịch bản before/after rõ ràng.
- [ ] Bảng so sánh số liệu STATISTICS IO/TIME trước và sau khi tối ưu.
- [ ] Báo cáo chi tiết lý do kỹ thuật.

---

## Giai đoạn 8 — Power BI & Insight

**Việc cần làm:**
1. Kết nối Power BI Desktop trực tiếp tới `DWH_Insurance`.
2. Xây model quan hệ trong Power BI khớp với Star Schema (bao gồm cả bảng dự đoán rủi ro ML).
3. Xây dashboard:
   - Xu hướng tổng phí thu / tổng bồi thường theo thời gian.
   - Loss ratio (bồi thường/phí) theo bang và sản phẩm bảo hiểm.
   - Phân tích rủi ro khách hàng: So sánh nhóm Rủi ro dự đoán (ML Risk Category) với Loss Ratio thực tế.
   - Xu hướng tổng phí thu / tổng bồi thường theo đặc tính xe và khu vực.
   - Loss ratio (bồi thường/phí) theo bang và nhóm xe.
   - Phân tích rủi ro xe cơ giới: So sánh nhóm Rủi ro dự đoán (ML Risk Category) với Loss Ratio thực tế.
4. Viết 3-5 insight tại `docs/reports/insights.md`.

**Definition of Done:**
- [ ] File `powerbi/insurance-dashboard.pbix`.
- [ ] Visual đối chiếu giữa rủi ro dự đoán và tổn thất thực tế.
- [ ] File `docs/reports/insights.md` có nhận định phân tích cụ thể.

---

## Cấu trúc thư mục chuẩn

```
insurance-dwh-project/
├── data/raw/                  # Dữ liệu thô SUSEP và Porto Seguro
├── data/raw/
│   ├── brvehins1/             # Dataset canonical (5 partition CSVs, ~1.965M rows, 23 cols)
│   │   ├── brvehins1a.csv
│   │   ├── brvehins1b.csv
│   │   ├── brvehins1c.csv
│   │   ├── brvehins1d.csv
│   │   └── brvehins1e.csv
│   └── susep.gov.br/          # Dataset legacy (~8.3M rows, ~751 MB; giu lai lam tai lieu lich su)
│       └── insurance_dataset.csv
├── docs/                      # Hệ thống tài liệu phân theo nhóm
│   ├── architecture/
│   ├── guides/
│   ├── reports/
│   └── specs/
├── ml/                        # Machine learning training và batch prediction
├── ml/                        # Machine learning training và batch prediction (STALE SCAFFOLD)
│   ├── train_risk_model.py
│   └── predict_risk_batch.py
├── notebooks/
│   └── 01-eda.ipynb
├── migrations/                # Schema migrations (Flyway/DbUp)
├── migrations/                # Schema migrations (Flyway/DbUp, STALE SCAFFOLD)
│   └── V1__create_dwh_schema.sql
├── sql/                       # Scripts staging, CDC, ETL, DQ và ML load
├── sql/                       # Scripts staging, CDC, ETL, DQ và ML load (STALE SCAFFOLD)
│   ├── 01_load_staging.sql
│   ├── 02_enable_cdc.sql
│   ├── 03_sp_dim_customer_scd2.sql
│   ├── 04_sp_dim_others.sql
│   ├── 05_sp_fact_premium.sql
│   ├── 06_sp_fact_claims.sql
│   ├── 07_data_quality_checks.sql
│   └── 08_sp_load_risk_predictions.sql
├── dags/
│   └── insurance_dwh_pipeline.py
│   └── insurance_dwh_pipeline.py # Airflow DAG (STALE SCAFFOLD)
├── powerbi/
│   └── insurance-dashboard.pbix
├── scripts/
│   └── validate_repo.py       # Repo static validator
├── docker-compose.yml
└── README.md
```
