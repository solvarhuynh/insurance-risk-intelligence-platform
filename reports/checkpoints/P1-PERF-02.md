# P1-PERF-02 — Index experiments SUSEP

## Thử nghiệm và kết quả

| Workload | Hypothesis / change | Before → after fact logical reads | CPU / elapsed | Decision |
|---|---|---:|---:|---|
| Q1 company trend | `IX_FactSusepInsuranceMarket_CompanyMonth_Perf (SusepCompanyKey,SusepMonthKey) INCLUDE(Premiums,Claims)` | 317.528 → 3.364 (−98,94%) | 1.320/176 ms → 127/129 ms | KEEP |
| Q2 state/product trend | `IX_FactSusepInsuranceMarket_StateProductMonth_Perf (SusepStateKey,SusepProductKey,SusepMonthKey) INCLUDE(Premiums,Claims)` | 317.528 → 3.734 (−98,82%) | 1.425/177 ms → 88/101 ms | KEEP |
| Q1 company trend | `SourceRecordHash` trial index | 3.364 → 3.364 (không cải thiện) | 127/129 ms → 143/146 ms | REJECT + DROP |

## Trade-off

- Retained company/month covering index: **454,04 MB**.
- Retained state/product/month covering index: **470,47 MB**.
- Rejected source-hash trial would dùng **639,23 MB** và không thuộc predicate của workload; đã bị drop.

Hai index retained làm write/load chậm và dùng gần 925 MB, nên chỉ hợp lý vì phục vụ hai query pattern được chứng minh. DQ production và fact/staging reconciliation vẫn pass sau thay đổi schema index.

## Stage này giải quyết vấn đề gì?

Chuyển baseline thành thí nghiệm có quyết định: mỗi index phải có hypothesis, số trước/sau, chi phí và verdict KEEP/REJECT. Đây giống thử một kệ hồ sơ mới: chỉ giữ kệ nếu nó giúp tìm đúng loại hồ sơ nhanh hơn chi phí diện tích.

## Trước stage này project thiếu gì?

P1-PERF-01 mới biết Q1/Q2 phải scan fact lớn; chưa biết composite key nào phù hợp hay index rộng không liên quan có gây lãng phí storage/write không.

## Agent đã sửa những file nào và tại sao?

- `migrations/V14__add_susep_performance_indexes.sql`: versioned retained indexes cho hai workload đã đo; migration được apply idempotent vào SQL Server.
- `reports/checkpoints/P1-PERF-02.md`: lưu every experiment và decision.
- `reports/performance-report.md`: diễn giải Vietnamese cho owner.

Source-hash trial index đã bị drop vì evidence không hỗ trợ nó; raw và fact grain không thay đổi.

## Data/code đi qua đâu?

```text
Q1/Q2 business query → baseline IO/TIME
  → composite covering-index hypothesis
  → create / rerun same query / inspect reads
  → DQ + reconciliation regression check
  → KEEP hoặc DROP
```

## Owner cần hiểu khái niệm gì?

**Covering index** mang theo key để filter/group và measure cần đọc, nên optimizer có thể tránh scan whole fact. **Trade-off** là index tăng tốc read nhưng giống tạo thêm mục lục: tốn disk và mỗi lần insert/load phải cập nhật thêm.

## Owner chưa cần học gì?

Chưa cần ép optimizer bằng hint hay tạo index cho mọi column. Các cách đó dễ làm performance xấu khi workload đổi.

## Owner tự kiểm tra thế nào?

1. Chạy exact Q1/Q2 và ghi `STATISTICS IO/TIME`.
2. Kiểm tra index retained đúng key/include theo checkpoint.
3. Chạy Track-A reconciliation và production DQ sau bất cứ DDL index nào.
4. Drop trial không giúp workload thay vì để nó âm thầm làm ETL nặng hơn.

## Điều gì có thể nhìn đúng nhưng thực ra sai?

Index `SourceRecordHash` có vẻ “nhiều thông tin” nhưng Q1 không filter hash, nên reads không đổi và CPU/elapsed còn tăng. “Nhiều index hơn” không đồng nghĩa “nhanh hơn”.

## Stage verdict

**PASS** — hai experiment có workload/evidence thật, một index không liên quan đã bị loại, và retained indexes có read reduction lớn.
