# P1-PERF-01 — Performance baseline SUSEP

## Stage này giải quyết vấn đề gì?

Đo workload thật trên 8.338.214-row Market fact trước tuning. Không suy luận “có index là nhanh”; dùng `SET STATISTICS IO/TIME` trên SQL Server.

## Trước stage này project thiếu gì?

Fact và DQ đã đúng nhưng chưa biết query market nào thực sự tốn đọc dữ liệu, cũng chưa có số trước thay đổi để đánh giá index sau này. Không có baseline thì “nhanh hơn” chỉ là cảm giác.

## Agent đã sửa những file nào và tại sao?

- `reports/checkpoints/P1-PERF-01.md`: lưu workload, điều kiện đo và số baseline để P1-PERF-02 không cherry-pick kết quả.
- `reports/performance-report.md`: tổng hợp cách đọc logical reads/CPU/elapsed cho owner.

Không tạo index ở stage này; baseline phải tồn tại trước khi can thiệp.

## Data/code đi qua đâu?

```text
FactSusepInsuranceMarket + dimension filter/group
  → SQL Server execution plan
  → SET STATISTICS IO/TIME output
  → baseline evidence
  → hypothesis index ở P1-PERF-02
```

## Baseline evidence

| Workload | Filter/grain | Fact logical reads | CPU / elapsed |
|---|---|---:|---:|
| Q1 company trend | `CompanyCode=6572` (HDI), từ 2018, group month | 317.528 | 1.320 ms / 176 ms |
| Q2 state-product trend | `SP` + `0588 - DPVAT`, từ 2018, group month | 317.528 | 1.425 ms / 177 ms |

Cả hai baseline scan large Fact vì chưa có index theo filter key. Data page đã warm (`physical reads=0` ở Q1), nên comparison về logical reads không bị che bởi disk-cache accident.

## Owner cần hiểu khái niệm gì?

**Logical read** là số trang data SQL Server phải mở, giống số ngăn hồ sơ phải lục. **Execution plan** là đường đi SQL chọn để trả lời query. CPU/elapsed có thể dao động theo cache/host load nên logical reads là thước đo chính khi so cùng query.

## Owner chưa cần học gì?

Chưa cần học mọi loại index hoặc partitioning. Chỉ cần biết business question, predicate/group và số đo trước là điều kiện để thí nghiệm có ý nghĩa.

## Owner tự kiểm tra thế nào?

Mở `P1-PERF-02.md` để lấy exact index/query decision, chạy lại workload với `SET STATISTICS IO ON; SET STATISTICS TIME ON;`, ghi cả logical reads lẫn CPU/elapsed. Không thay filter/query giữa before và after.

## Điều gì có thể nhìn đúng nhưng thực ra sai?

Một lần elapsed thấp có thể chỉ là cache ấm. Index tồn tại cũng không chứng minh optimizer dùng nó. Vì vậy baseline ghi filter/grain, warm-cache observation và read count thay vì chỉ ảnh chụp execution plan.

## Stage verdict

**PASS** — có baseline reproducible, row-level SQL workload và IO/TIME evidence trước thay đổi.
