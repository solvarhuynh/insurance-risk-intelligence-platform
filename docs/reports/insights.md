# Insight nghiệp vụ — chờ dữ liệu DWH

Trạng thái: `SCAFFOLD`.

Insight chỉ được viết sau khi DWH có dữ liệu đã đối soát và Data Quality gate đã pass. Các phân tích dự kiến phải dựa trên số liệu thực tế, gồm:

1. Exposure, premium và claim theo bang, khu vực, nhóm xe và nhóm tuổi người lái.
2. Claim frequency theo exposure dương và loss ratio theo premium dương.
3. Các quan sát chất lượng dữ liệu hoặc bất thường có bằng chứng, không gán nhãn outlier là lỗi khi chưa có contract.

Không có insight, threshold nghiệp vụ hoặc kết quả ML nào được xem là đã chứng minh trước khi các stage dữ liệu nền tảng hoàn tất.
