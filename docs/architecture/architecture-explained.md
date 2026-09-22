# Kiến trúc dự án, giải thích theo luồng dữ liệu (brvehins1)

## Dự án này giải quyết việc gì?

Dự án xây dựng một **Motor Insurance Data Warehouse** kết hợp **Machine Learning Batch Pipeline**: kho dữ liệu được tổ chức chuẩn mực theo mô hình Star Schema trên Microsoft SQL Server để phục vụ báo cáo phân tích rủi ro và tổn thất bảo hiểm xe cơ giới. Nguồn dữ liệu thực tế được sử dụng là **brvehins1** (từ hệ sinh thái CASdatasets / AUTOSEG / SUSEP), quy mô ~1.965 triệu dòng dữ liệu chia làm 5 phân đoạn CSV (`brvehins1[a-e].csv`), ghi nhận mức độ phơi nhiễm (exposure), doanh thu phí và các vụ bồi thường tổn thất xe theo nhóm người lái, dòng xe và khu vực địa lý tại Brazil.

Mục tiêu là xây dựng một hệ thống End-to-End trọn vẹn: quy trình nạp Staging, luồng ETL tự động với CDC, kiểm tra chất lượng dữ liệu (DQ Check), đo lường và tối ưu hóa hiệu năng (Performance Tuning), và xây dựng luồng dự đoán rủi ro (Batch Inference) phục vụ trực tiếp cho báo cáo phân tích Power BI.

---

## Dữ liệu đi từ đâu đến đâu?

```text
Raw brvehins1 (5 partitions: brvehins1[a-e].csv ~1.965M rows)
                    |
                    v
    Staging_InsuranceRaw trong SQL Server (stg_brvehins1)
                    |
                    v
            DWH_Insurance:
    Dimensions: Dim_Driver, Dim_Vehicle, Dim_Geography
    Facts: Fact_Policy_Exposure, Fact_Claims, Fact_Risk_Prediction
                    |
                    +------------------------------------------+
                    |                                          |
                    v                                          v
      Kiểm tra chất lượng dữ liệu (DQ Check)           ML Feature View (SQL)
                    |                                          |
                    v                                          v
      Airflow điều phối toàn bộ pipeline               Batch Model Scoring
                    |                              (ml/predict_risk_batch.py)
                    |                                          |
                    +<-----------------------------------------+
                    | (Lưu kết quả dự đoán)
                    v
          Fact_Risk_Prediction
                    |
                    +--> Đo và tối ưu truy vấn SQL (Tuning)
                    |
                    v
      Power BI: Dashboard tổn thất, xu hướng & rủi ro dự đoán
```

1. **Dữ liệu nguồn canonical**: Tập dữ liệu `brvehins1` (5 phân đoạn CSV trong `data/raw/brvehins1/`, tổng 1.965.355 dòng, 23 cột). Nguồn dữ liệu cũ `data/raw/susep.gov.br/insurance_dataset.csv` được lưu trữ dưới dạng **LEGACY / NON-CANONICAL** và không thuộc luồng dữ liệu xử lý.
2. **Staging**: 5 phân đoạn CSV được nạp nguyên trạng vào database `Staging_InsuranceRaw` bằng lệnh `BULK INSERT`.
3. **DWH Star Schema**: Các Stored Procedure T-SQL chuyển dữ liệu từ staging vào kho `DWH_Insurance`, áp dụng CDC để chỉ xử lý dữ liệu mới/thay đổi và nạp vào các bảng Dimension và Fact.
4. **Data Quality**: Pipeline tự động kiểm tra các quy tắc toàn vẹn (Not Null, Unique, Referential Integrity, Range check đối với phí và bồi thường) và ghi log vào `DQ_Check_Log`.
5. **Machine Learning Batch Inference**: Task Airflow gọi `ml/predict_risk_batch.py` trích xuất feature từ DWH, tính toán rủi ro tổn thất theo hồ sơ xe/người lái và lưu kết quả vào bảng sự kiện dự đoán.
6. **Analytics & Performance Tuning**: DWH được tối ưu truy vấn bằng Indexing/Partitioning trên tập dữ liệu ~2 triệu dòng, và trực quan hóa toàn diện trên Power BI Desktop.

---

## Các quyết định thiết kế

### Star Schema xoay quanh thực thể xe cơ giới
- Dùng **Star Schema** với các bảng chiều (`Dim_Driver`, `Dim_Vehicle`, `Dim_Geography`) và các bảng sự kiện (`Fact_Policy_Exposure`, `Fact_Claims`, `Fact_Risk_Prediction`). Mô hình này bám sát cấu trúc tự nhiên của `brvehins1` (không tự bịa đặt CustomerId hay PolicyNumber vốn không tồn tại trong dữ liệu gốc), tối ưu hóa cho truy vấn phân tích Loss Ratio và tần suất bồi thường.

### CDC (Change Data Capture) thay vì nạp lại toàn bộ
- Nguồn dữ liệu gồm gần 2 triệu dòng. Áp dụng **CDC** và cơ chế Watermark giúp chỉ nạp phần dữ liệu mới/thay đổi, tiết kiệm I/O đĩa và rút ngắn thời gian chạy batch.

### Machine Learning Batch Inference tích hợp vào Airflow
- Thay vì tách rời mô hình ML, dự án xem DWH như một **Feature Store**. Airflow điều phối việc chạy model scoring định kỳ và ghi ngược kết quả vào DWH để Power BI có thể so sánh giữa *Rủi ro dự đoán* và *Tổn thất thực tế*.

### Audit Log và Idempotency
- Mọi Stored Procedure đều được bọc trong khối `TRY...CATCH`, ghi nhận nhật ký vào `ETL_Audit_Log` và sử dụng lệnh `MERGE` để đảm bảo tính idempotent: chạy lại cùng một batch không gây trùng lặp hay sai lệch số liệu.

### Tối ưu truy vấn bằng Index dựa trên đo đạc thực tế
- Trên Fact Table quy mô ~2 triệu dòng, việc đo lường Execution Plan và `STATISTICS IO, TIME` trước và sau khi tạo Index giúp chứng minh rõ ràng năng lực Performance Tuning.

### Định vị dữ liệu Legacy (susep.gov.br)
- File `data/raw/susep.gov.br/insurance_dataset.csv` là dữ liệu báo cáo thống kê thị trường vĩ mô từ dự án trước. File này được bảo toàn nguyên vẹn trong thư mục raw nhưng được gắn nhãn LEGACY, không tham gia vào pipeline canonical `brvehins1`.
