# Bảng thuật ngữ

| Thuật ngữ | Giải thích ngắn | Xuất hiện ở đâu trong dự án |
|---|---|---|
| Data Warehouse | Kho dữ liệu được tổ chức cho mục đích phân tích và báo cáo, tách khỏi dữ liệu thô/vận hành. | `DWH_Insurance`, `migrations/V1__create_dwh_schema.sql` |
| Star Schema | Mô hình dữ liệu có Fact ở trung tâm và các Dimension bao quanh như hình ngôi sao. | Thiết kế Giai đoạn 3; `migrations/V1__create_dwh_schema.sql` |
| Fact table | Bảng ghi các sự kiện có số đo để cộng, đếm hoặc phân tích. | `Fact_Premium`, `Fact_Claims` |
| Dimension table | Bảng chứa thuộc tính mô tả để phân nhóm và lọc Fact. | `Dim_Customer`, `Dim_Policy`, `Dim_Date`, `Dim_Region` |
| SCD Type 2 | Cách lưu lịch sử thay đổi của Dimension bằng cách tạo phiên bản dòng mới thay vì ghi đè dòng cũ. | `Dim_Customer`; `sql/03_sp_dim_customer_scd2.sql` |
| Surrogate key | Khoá kỹ thuật do kho dữ liệu tạo, thường là số tăng dần, để liên kết ổn định giữa Fact và Dimension. | Các cột như `CustomerKey`, `PolicyKey` trong migration |
| Business key | Mã định danh có ý nghĩa nghiệp vụ từ nguồn, ví dụ mã khách hàng hay mã sản phẩm. | `CustomerId`, `PolicyNumber`, `RegionCode` |
| Fact table | Bảng ghi các sự kiện có số đo để cộng, đếm hoặc phân tích. | `Fact_Policy_Risk` (mô hình canonical `brvehins1`); `Fact_Premium`, `Fact_Claims` (scaffold cũ) |
| Dimension table | Bảng chứa thuộc tính mô tả để phân nhóm và lọc Fact. | `Dim_Driver_Profile`, `Dim_Vehicle`, `Dim_Geography` (canonical `brvehins1`); `Dim_Customer`, `Dim_Policy` (scaffold cũ) |
| SCD Type 2 | Cách lưu lịch sử thay đổi của Dimension bằng cách tạo phiên bản dòng mới thay vì ghi đè dòng cũ. | Mô hình scaffold cũ (`Dim_Customer`; `sql/03_sp_dim_customer_scd2.sql`); dữ liệu `brvehins1` không có chuỗi thời gian khách hàng |
| Surrogate key | Khoá kỹ thuật do kho dữ liệu tạo, thường là số tăng dần, để liên kết ổn định giữa Fact và Dimension. | Các cột như `DriverProfileKey`, `VehicleKey`, `GeographyKey` |
| Business / Natural key | Mã định danh có ý nghĩa nghiệp vụ từ nguồn. | Tổ hợp tự nhiên trong `brvehins1`: `(Gender, DrivAge)`, `(VehYear, VehModel, VehGroup)`, `(Area, State, StateAb)`; các khóa `CustomerId`, `PolicyNumber` thuộc mô hình scaffold cũ |
| Exposure | Thời gian đơn vị xe chịu rủi ro bảo hiểm (thường đo bằng năm xe, ví dụ 0.5 = 6 tháng). Đại lượng cơ sở để chuẩn hóa tần suất rủi ro. | Các cột `ExposTotal`, `ExposFireRob` trong `brvehins1` |
| Claim Frequency & Severity | Tần suất số vụ bồi thường trên exposure (Claims / Exposure) và tổn thất bình quân trên mỗi vụ claim (Claim Amount / Claim Count). | Các cột `ClaimNb*` và `ClaimAmount*` trong `brvehins1` |
| CDC (Change Data Capture) | Cơ chế ghi nhận các hàng đã thay đổi để ETL chỉ xử lý phần mới/sửa thay vì đọc lại toàn bộ. | `sql/02_enable_cdc.sql`; Giai đoạn 4 |
| Watermark | Mốc của lần xử lý thành công gần nhất, dùng để xác định dữ liệu nào chưa được lấy. | Bảng `ETL_Watermark` trong `sql/02_enable_cdc.sql` |
| Idempotency | Tính chất chạy lại cùng một batch vẫn cho cùng kết quả, không nhân đôi dữ liệu. | Các thủ tục ETL Giai đoạn 4 |
| Audit log | Nhật ký vận hành lưu thông tin lần chạy, số dòng, trạng thái và lỗi để truy vết. | `ETL_Audit_Log` trong các script ETL |
| Execution Plan | Kế hoạch SQL Server chọn để thực hiện truy vấn, cho biết các bước như quét bảng hay nối bảng. | Giai đoạn 7; `README.md` |
| Non-Clustered Index | Cấu trúc tra cứu phụ tách khỏi dữ liệu chính, giúp tìm nhanh theo một số cột nhưng có chi phí khi ghi. | Đã lên kế hoạch ở Giai đoạn 7 |
| Covering Index | Non-Clustered Index chứa đủ cột truy vấn cần, giảm nhu cầu quay lại bảng chính lấy dữ liệu. | Đã lên kế hoạch ở Giai đoạn 7 |
| Loss Ratio | Tỷ lệ giá trị bồi thường trên giá trị phí bảo hiểm; tỷ lệ cao có thể cho thấy rủi ro hoặc định phí cần xem xét. | Dashboard/insight dự kiến Giai đoạn 8 |
| DAG | Đồ thị có hướng không vòng lặp, dùng để mô tả thứ tự phụ thuộc giữa các task trong Airflow. | `dags/insurance_dwh_pipeline.py` |
| Orchestration | Việc điều phối các task theo thứ tự, lịch chạy, retry và xử lý lỗi. | Airflow; `dags/insurance_dwh_pipeline.py` |
| Data Quality check | Quy tắc tự động phát hiện dữ liệu không đạt yêu cầu, ví dụ thiếu khoá hoặc số tiền âm. | `sql/07_data_quality_checks.sql` |

