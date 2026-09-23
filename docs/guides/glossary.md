# Bảng thuật ngữ theo dự án

| Thuật ngữ | Ý nghĩa trong dự án |
|---|---|
| Raw | Năm file CSV `brvehins1` bất biến trong `data/raw/brvehins1/`. |
| Staging | Bản sao có kiểm soát trong SQL Server, giữ 23 trường nguồn cùng metadata ingest. |
| Grain | Ý nghĩa chính xác của một dòng dữ liệu; phải được EDA chốt trước khi tạo fact. |
| Dimension | Bảng mô tả nhóm thuộc tính thực, ví dụ người lái, xe hoặc địa lý nếu contract chứng minh phù hợp. |
| Fact | Bảng số đo ở grain đã chốt, gồm exposure, premium, sum insured và claim. |
| Surrogate key | Khóa do kho dữ liệu sinh để liên kết fact với dimension; không thay thế business identifier. |
| Technical record identity | Khóa kỹ thuật truy vết về file và dòng nguồn khi nguồn không cung cấp business identifier. |
| Batch | Một lần nạp một partition có metadata, số dòng nguồn, số dòng staging và trạng thái. |
| Idempotency | Chạy lại cùng batch không sinh thêm dữ liệu hoặc làm thay đổi tổng hợp ngoài chủ ý. |
| Reconciliation | Đối chiếu số dòng và số đo giữa raw, staging và fact. |
| Data Quality gate | Tập rule thực thi được; hard failure chặn bước pipeline tiếp theo. |
| Claim frequency | Số vụ claim trên exposure, chỉ xác định khi exposure dương. |
| Loss ratio | Tổng claim amount chia premium, chỉ xác định khi premium dương. |

Các thuật ngữ chỉ mô tả dữ liệu và hành vi đã có bằng chứng. Nội dung ML, orchestration, tuning và BI sẽ được mở rộng sau foundation.
