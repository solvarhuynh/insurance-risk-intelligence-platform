# Báo cáo Performance Tuning — Track A SUSEP

## Tóm tắt cho owner

Performance tuning không phải là “tạo index cho có”. Đây là quá trình đo một workload thật, giả thuyết nguyên nhân chậm, thay đổi có giới hạn, rồi đo lại trong cùng SQL Server. Track A được chọn vì `dwh.FactSusepInsuranceMarket` có 8.338.214 fact rows — đủ lớn để chứng minh lợi ích và chi phí của index.

## Workloads đã đo

Mỗi workload aggregate premium/claims từ fact, join các dimension cần thiết và filter theo các key xuất hiện trong điều kiện thực tế. Đo bằng `SET STATISTICS IO ON` và `SET STATISTICS TIME ON`; logical reads là số trang SQL Server phải đọc, giống số ngăn hồ sơ phải mở để trả lời một câu hỏi.

| Query | Nhu cầu phân tích | Before | Thay đổi giữ lại | After | Quyết định |
|---|---|---:|---|---:|---|
| Q1 — company trend | Premium/claims theo company và month | 317.528 logical reads; CPU/elapsed 1.320/176 ms | `IX_FactSusepInsuranceMarket_CompanyMonth_Perf (SusepCompanyKey,SusepMonthKey) INCLUDE(Premiums,Claims)` | 3.364 reads; CPU/elapsed 127/129 ms | KEEP |
| Q2 — state/product trend | Premium/claims theo state, product, month | 317.528 logical reads; CPU/elapsed 1.425/177 ms | `IX_FactSusepInsuranceMarket_StateProductMonth_Perf (SusepStateKey,SusepProductKey,SusepMonthKey) INCLUDE(Premiums,Claims)` | 3.734 reads; CPU/elapsed 88/101 ms | KEEP |

Q1 giảm **98,94%** logical reads; Q2 giảm **98,82%**. Runtime nhỏ còn phụ thuộc cache và host load nên logical reads là bằng chứng chính, còn CPU/elapsed là bằng chứng bổ trợ.

## Thử nghiệm bị loại

| Trial | Giả thuyết | Kết quả | Quyết định |
|---|---|---|---|
| Index `SourceRecordHash` cho Q1 | Hash có thể giúp tăng tốc trend theo company/month | Reads vẫn 3.364; CPU/elapsed tăng từ 127/129 lên 143/146 ms; storage 639,23 MB | REJECT và DROP |

Lý do: predicate và group của Q1 không sử dụng source hash. Một index rộng 639 MB chỉ làm tăng chi phí write/load mà không giúp workload này.

## Trade-off đã chấp nhận

- Company/month covering index chiếm khoảng **454,04 MB**.
- State/product/month covering index chiếm khoảng **470,47 MB**.
- Hai index làm insert/ETL tốn thêm thời gian và cần gần **925 MB** storage tổng cộng.

Đổi lại, chúng phục vụ hai query pattern đã được đo. Reconciliation source→staging→fact và production DQ được chạy lại sau thay đổi, nên lợi ích không đánh đổi integrity.

Hai quyết định `KEEP` được lưu có thể tái áp dụng bằng migration idempotent `migrations/V14__add_susep_performance_indexes.sql`; migration chỉ tạo index nếu chưa có và không thay đổi fact grain hay Track B.

## Cách tự kiểm tra

1. Mở `reports/checkpoints/P1-PERF-01.md` để xem baseline và `P1-PERF-02.md` để xem thí nghiệm.
2. Chạy lại đúng query trong checkpoint với `SET STATISTICS IO, TIME ON`.
3. So sánh logical reads, không chỉ nhìn một lần elapsed time nhanh do cache.
4. Chỉ giữ index khi query pattern và trade-off storage/write được giải thích rõ.

## Kết luận

**PASS.** Hai index có hiệu quả đo được trên Track A, một trial không phù hợp đã được drop, và DWH/DQ không regressed. Đây là performance evidence cho market DWH; không suy diễn nó thành benchmark cho Track B hoặc Power BI refresh.
